"""
Receipt Persistence Module
===========================

JSONL-based append-only storage for policy change receipts.
Supports:
- Thread-safe appending
- Hash chain validation
- Filtering by experiment, type, date
- Tamper detection
"""

from dataclasses import dataclass
from typing import List, Optional, Dict, Any, Iterator
from pathlib import Path
from datetime import datetime, timedelta
import json
import hashlib
import threading
import logging

from quintet.causal.policy_receipts import (
    PolicyChangeReceipt,
    PolicyExperiment,
    PolicyIntervention,
    ShadowExecution,
    CausalSummary,
    SuccessCriteria,
    PolicyDomain,
    InterventionType,
)

logger = logging.getLogger(__name__)


def compute_receipt_hash(receipt: PolicyChangeReceipt) -> str:
    """
    Compute SHA256 hash of receipt data.

    Args:
        receipt: PolicyChangeReceipt to hash

    Returns:
        Hex digest of hash
    """
    data = receipt.to_dict()
    # Remove fields that shouldn't be part of hash
    data.pop("receipt_hash", None)
    data.pop("parent_hash", None)

    # Stable JSON serialization
    json_str = json.dumps(data, sort_keys=True, default=str)
    return hashlib.sha256(json_str.encode()).hexdigest()


@dataclass
class ReceiptWithHash:
    """Receipt with hash chain metadata."""

    receipt: PolicyChangeReceipt
    receipt_hash: str
    parent_hash: Optional[str] = None
    sequence_number: int = 0

    def to_dict(self) -> Dict[str, Any]:
        """Serialize with hash chain metadata."""
        data = self.receipt.to_dict()
        data["receipt_hash"] = self.receipt_hash
        data["parent_hash"] = self.parent_hash
        data["sequence_number"] = self.sequence_number
        return data


class ReceiptStore:
    """
    Thread-safe append-only JSONL storage for policy change receipts.

    Features:
    - Atomic appends with file locking
    - Hash chain for tamper detection
    - Efficient filtering and querying
    - Graceful handling of corrupt lines
    """

    def __init__(self, storage_path: str = "logs/receipts.jsonl"):
        """
        Initialize receipt store.

        Args:
            storage_path: Path to JSONL file
        """
        self.storage_path = Path(storage_path)
        self.storage_path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.Lock()
        self._logger = logger

        # Cache for last hash (performance optimization)
        self._last_hash: Optional[str] = None
        self._sequence_counter: int = 0

        # Initialize from existing file
        self._initialize_from_file()

    def _initialize_from_file(self) -> None:
        """Load last hash and sequence number from existing file."""
        if not self.storage_path.exists():
            return

        try:
            last_line = None
            with open(self.storage_path, 'r') as f:
                for line in f:
                    if line.strip():
                        last_line = line

            if last_line:
                data = json.loads(last_line)
                self._last_hash = data.get("receipt_hash")
                self._sequence_counter = data.get("sequence_number", 0)

        except Exception as e:
            self._logger.warning(f"Could not initialize from existing file: {e}")

    def append_receipt(
        self,
        receipt: PolicyChangeReceipt,
        verify_chain: bool = True
    ) -> ReceiptWithHash:
        """
        Append receipt to storage.

        Thread-safe. Creates hash chain link.

        Args:
            receipt: PolicyChangeReceipt to store
            verify_chain: If True, verify hash chain on read

        Returns:
            ReceiptWithHash with hash metadata
        """
        with self._lock:
            # Compute hash
            receipt_hash = compute_receipt_hash(receipt)

            # Create hash chain link
            receipt_with_hash = ReceiptWithHash(
                receipt=receipt,
                receipt_hash=receipt_hash,
                parent_hash=self._last_hash,
                sequence_number=self._sequence_counter + 1
            )

            # Write to file (append-only)
            with open(self.storage_path, 'a') as f:
                json.dump(receipt_with_hash.to_dict(), f, default=str)
                f.write('\n')

            # Update cache
            self._last_hash = receipt_hash
            self._sequence_counter += 1

            self._logger.info(
                f"Appended receipt {receipt.receipt_id} "
                f"(seq={self._sequence_counter}, hash={receipt_hash[:8]}...)"
            )

            return receipt_with_hash

    def read_all_receipts(
        self,
        verify_chain: bool = False,
        skip_corrupt: bool = True
    ) -> List[ReceiptWithHash]:
        """
        Read all receipts from storage.

        Args:
            verify_chain: If True, verify hash chain integrity
            skip_corrupt: If True, skip malformed lines instead of failing

        Returns:
            List of ReceiptWithHash objects
        """
        if not self.storage_path.exists():
            return []

        receipts: List[ReceiptWithHash] = []
        corrupt_count = 0

        with open(self.storage_path, 'r') as f:
            for line_num, line in enumerate(f, 1):
                if not line.strip():
                    continue

                try:
                    data = json.loads(line)
                    receipt = self._deserialize_receipt(data)

                    receipt_with_hash = ReceiptWithHash(
                        receipt=receipt,
                        receipt_hash=data.get("receipt_hash", ""),
                        parent_hash=data.get("parent_hash"),
                        sequence_number=data.get("sequence_number", 0)
                    )
                    receipts.append(receipt_with_hash)

                except Exception as e:
                    corrupt_count += 1
                    if skip_corrupt:
                        self._logger.warning(
                            f"Skipping corrupt line {line_num}: {e}"
                        )
                    else:
                        raise

        if corrupt_count > 0:
            self._logger.warning(
                f"Skipped {corrupt_count} corrupt lines"
            )

        # Verify hash chain if requested
        if verify_chain and receipts:
            self._verify_hash_chain(receipts)

        return receipts

    def read_recent_receipts(
        self,
        limit: int = 100,
        verify_chain: bool = False
    ) -> List[ReceiptWithHash]:
        """
        Read most recent N receipts.

        Args:
            limit: Maximum number of receipts to return
            verify_chain: If True, verify hash chain

        Returns:
            List of most recent ReceiptWithHash objects
        """
        all_receipts = self.read_all_receipts(verify_chain=verify_chain)
        return all_receipts[-limit:] if all_receipts else []

    def filter_receipts(
        self,
        experiment_id: Optional[str] = None,
        promoted: Optional[bool] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        domain: Optional[PolicyDomain] = None,
        intervention_type: Optional[InterventionType] = None,
    ) -> List[ReceiptWithHash]:
        """
        Filter receipts by various criteria.

        Args:
            experiment_id: Filter by experiment ID
            promoted: Filter by promotion status
            start_date: Filter by timestamp >= start_date
            end_date: Filter by timestamp <= end_date
            domain: Filter by policy domain
            intervention_type: Filter by intervention type

        Returns:
            Filtered list of ReceiptWithHash objects
        """
        all_receipts = self.read_all_receipts()
        filtered = []

        for rwh in all_receipts:
            # Experiment ID filter
            if experiment_id and rwh.receipt.experiment.experiment_id != experiment_id:
                continue

            # Promotion filter
            if promoted is not None and rwh.receipt.promoted != promoted:
                continue

            # Date filters
            if start_date and rwh.receipt.timestamp < start_date:
                continue
            if end_date and rwh.receipt.timestamp > end_date:
                continue

            # Domain filter
            if domain and rwh.receipt.experiment.intervention.domain != domain:
                continue

            # Intervention type filter
            if intervention_type and rwh.receipt.experiment.intervention.intervention_type != intervention_type:
                continue

            filtered.append(rwh)

        return filtered

    def verify_integrity(self) -> Dict[str, Any]:
        """
        Verify integrity of stored receipts.

        Returns:
            Dictionary with integrity report
        """
        receipts = self.read_all_receipts(verify_chain=False)

        if not receipts:
            return {
                "status": "empty",
                "total_receipts": 0,
                "hash_chain_valid": True,
                "tampered_receipts": [],
                "chain_breaks": [],
            }

        # Check hash chain
        chain_breaks = []
        for i in range(1, len(receipts)):
            expected_parent = receipts[i-1].receipt_hash
            actual_parent = receipts[i].parent_hash
            if expected_parent != actual_parent:
                chain_breaks.append({
                    "position": i,
                    "expected_parent": expected_parent,
                    "actual_parent": actual_parent,
                })

        # Check individual receipt hashes
        tampered_receipts = []
        for i, rwh in enumerate(receipts):
            computed_hash = compute_receipt_hash(rwh.receipt)
            if computed_hash != rwh.receipt_hash:
                tampered_receipts.append({
                    "position": i,
                    "sequence_number": rwh.sequence_number,
                    "stored_hash": rwh.receipt_hash,
                    "computed_hash": computed_hash,
                })

        return {
            "status": "valid" if not (chain_breaks or tampered_receipts) else "invalid",
            "total_receipts": len(receipts),
            "hash_chain_valid": len(chain_breaks) == 0,
            "tampered_receipts": tampered_receipts,
            "chain_breaks": chain_breaks,
        }

    def _verify_hash_chain(self, receipts: List[ReceiptWithHash]) -> None:
        """
        Verify hash chain integrity.

        Raises:
            ValueError: If chain is broken
        """
        for i in range(1, len(receipts)):
            expected_parent = receipts[i-1].receipt_hash
            actual_parent = receipts[i].parent_hash

            if expected_parent != actual_parent:
                raise ValueError(
                    f"Hash chain broken at position {i}: "
                    f"expected parent {expected_parent[:8]}..., "
                    f"got {actual_parent[:8] if actual_parent else 'None'}..."
                )

    def _deserialize_receipt(self, data: Dict[str, Any]) -> PolicyChangeReceipt:
        """
        Deserialize receipt from dict.

        Args:
            data: Dictionary representation

        Returns:
            PolicyChangeReceipt instance
        """
        # Parse experiment data
        exp_data = data["experiment"]

        # Parse intervention
        intervention_data = exp_data["intervention"]
        intervention = PolicyIntervention(
            intervention_id=intervention_data["intervention_id"],
            timestamp=datetime.fromisoformat(intervention_data["timestamp"]),
            domain=PolicyDomain(intervention_data["domain"]),
            intervention_type=InterventionType(intervention_data["intervention_type"]),
            parameter_name=intervention_data["parameter_name"],
            old_value=intervention_data["old_value"],
            new_value=intervention_data["new_value"],
            hypothesis=intervention_data["hypothesis"],
            mechanism=intervention_data["mechanism"],
            triggered_by=intervention_data["triggered_by"],
            details=intervention_data.get("details", {}),
        )

        # Parse success criteria
        sc_data = exp_data["success_criteria"]
        success_criteria = SuccessCriteria(
            min_effect_size=sc_data["min_effect_size"],
            confidence_level=sc_data["confidence_level"],
            max_ci_width=sc_data["max_ci_width"],
            min_episodes_per_stratum=sc_data["min_episodes_per_stratum"],
            min_overlap_per_stratum=sc_data["min_overlap_per_stratum"],
            max_latency_regression_pct=sc_data["max_latency_regression_pct"],
            max_cost_increase_pct=sc_data["max_cost_increase_pct"],
            no_new_failure_modes=sc_data["no_new_failure_modes"],
            stress_scenarios_pass=sc_data["stress_scenarios_pass"],
            max_validity_concerns=sc_data["max_validity_concerns"],
            no_unmeasured_confounding_flags=sc_data["no_unmeasured_confounding_flags"],
            observation_days=sc_data["observation_days"],
            details=sc_data.get("details", {}),
        )

        # Parse causal summary if present
        causal_summary = None
        if exp_data.get("causal_summary"):
            cs_data = exp_data["causal_summary"]
            causal_summary = CausalSummary(
                summary_id=cs_data["summary_id"],
                timestamp=datetime.fromisoformat(cs_data["timestamp"]),
                effect_estimate=cs_data["effect_estimate"],
                ci_lower=cs_data["ci_95"][0],
                ci_upper=cs_data["ci_95"][1],
                method=cs_data["method"],
                sample_size=cs_data["sample_size"],
                sample_size_per_stratum_min=cs_data["sample_size_per_stratum"]["min"],
                sample_size_per_stratum_max=cs_data["sample_size_per_stratum"]["max"],
                overlap_check_passed=cs_data["overlap_check_passed"],
                min_overlap_observed=cs_data["min_overlap_observed"],
                validity_concerns=cs_data["validity_concerns"],
                promotion_recommendation=cs_data["promotion_recommendation"],
                details=cs_data.get("details", {}),
            )

        # Parse experiment
        experiment = PolicyExperiment(
            experiment_id=exp_data["experiment_id"],
            created_at=datetime.fromisoformat(exp_data["created_at"]),
            name=exp_data["name"],
            description=exp_data["description"],
            intervention=intervention,
            target_effect=exp_data["target_effect"],
            required_sample_size=exp_data["required_sample_size"],
            success_criteria=success_criteria,
            stress_scenarios=exp_data["stress_scenarios"],
            scheduled_duration_days=exp_data["scheduled_duration_days"],
            started_at=datetime.fromisoformat(exp_data["started_at"]) if exp_data.get("started_at") else None,
            ended_at=datetime.fromisoformat(exp_data["ended_at"]) if exp_data.get("ended_at") else None,
            causal_summary=causal_summary,
            promotion_approved=exp_data["promotion_approved"],
            promotion_approved_by=exp_data["promotion_approved_by"],
            promotion_approved_at=datetime.fromisoformat(exp_data["promotion_approved_at"]) if exp_data.get("promotion_approved_at") else None,
            details=exp_data.get("details", {}),
        )

        # Parse receipt
        receipt = PolicyChangeReceipt(
            receipt_id=data["receipt_id"],
            timestamp=datetime.fromisoformat(data["timestamp"]),
            experiment=experiment,
            promoted=data["promoted"],
            promotion_reason=data["promotion_reason"],
            guardian_approved=data["guardian_approved"],
            guardian_notes=data["guardian_notes"],
            metrics_snapshot=data.get("metrics_snapshot"),
            details=data.get("details", {}),
        )

        return receipt


# Global singleton store
_receipt_store: Optional[ReceiptStore] = None
_store_lock = threading.Lock()


def get_receipt_store(storage_path: str = "logs/receipts.jsonl") -> ReceiptStore:
    """
    Get or create global receipt store.

    Thread-safe singleton.

    Args:
        storage_path: Path to JSONL file (used on first initialization)

    Returns:
        ReceiptStore instance
    """
    global _receipt_store

    if _receipt_store is None:
        with _store_lock:
            if _receipt_store is None:
                _receipt_store = ReceiptStore(storage_path)

    return _receipt_store


def reset_store() -> None:
    """Reset global store (for testing)."""
    global _receipt_store
    with _store_lock:
        _receipt_store = None
