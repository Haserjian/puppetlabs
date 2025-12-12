"""
Validation Receipts: Proof that validation invariants passed.

Each validation phase (Phase 1, 2, 3, etc.) mints a ValidationReceipt
linking test conditions → invariants checked → results obtained.

This turns "validation passed" from a log line into a first-class receipt
in the Receipt Internet, so later phases can reason about provable state.
"""

from __future__ import annotations

from dataclasses import dataclass, field, asdict
from datetime import datetime
from typing import Any, Dict, List, Optional
import hashlib
import json
import uuid


@dataclass
class ValidationReceipt:
    """
    Base class for validation receipts.

    A receipt proves that a set of invariants were checked at a point in time
    under specific conditions, with specific results.
    """

    receipt_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    timestamp: datetime = field(default_factory=datetime.utcnow)
    phase: str = ""  # "phase1", "phase2", etc.
    passed: bool = False
    checks: Dict[str, bool] = field(default_factory=dict)  # check_name -> passed
    warnings: List[str] = field(default_factory=list)
    failures: List[str] = field(default_factory=list)
    details: Dict[str, Any] = field(default_factory=dict)

    def compute_hash(self) -> str:
        """Compute SHA256 hash of this receipt's immutable content."""
        # Exclude receipt_id and hash itself to allow idempotent hashing
        data = asdict(self)
        data.pop("receipt_id", None)

        # Convert datetime to ISO string for hashing
        if isinstance(data.get("timestamp"), datetime):
            data["timestamp"] = data["timestamp"].isoformat()

        json_str = json.dumps(data, sort_keys=True, default=str)
        return hashlib.sha256(json_str.encode()).hexdigest()

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dict for storage/transmission."""
        data = asdict(self)
        if isinstance(data.get("timestamp"), datetime):
            data["timestamp"] = data["timestamp"].isoformat()
        return data


@dataclass
class Phase1ValidationReceipt(ValidationReceipt):
    """
    Proof that Phase 1 invariants (1-4) were checked on a specific fixture.

    Records:
      - Which fixture was tested (and its hash for reproducibility)
      - Which 4 invariants were checked
      - Whether each passed/warned/failed
      - Tool version for auditability
    """

    phase: str = "phase1"

    # What was tested
    fixture_path: str = ""
    fixture_hash: str = ""  # SHA256 of the fixture JSON
    fixture_episode_count: int = 0

    # Specific Phase 1 invariants checked
    check_episode_quality: bool = False
    check_recommendations: bool = False
    check_stress_gates: bool = False  # Note: may pass despite warning
    check_receipt_chain: bool = False

    # Tool & environment
    tool_version: str = ""  # git hash or version
    quintet_version: str = ""


@dataclass
class Phase2ValidationReceipt(ValidationReceipt):
    """
    Proof that Phase 2 invariants (5-7) were checked on a live system.

    Records:
      - Loom configuration tested against
      - Quintet configuration tested against
      - Whether each of 3 new invariants passed
      - Observed metrics and side effects
    """

    phase: str = "phase2"

    # What systems were tested
    loom_profile: str = ""  # e.g., "local-test", "staging"
    loom_config_hash: str = ""
    quintet_config_hash: str = ""

    # Specific Phase 2 invariants checked
    check_live_path: bool = False  # Invariant 5: Loom → Quintet call occurred
    check_policy_effect: bool = False  # Invariant 6: Effect observable + receipted
    check_failure_mode: bool = False  # Invariant 7: Misconfiguration caught

    # Observed effects
    quintet_calls_observed: int = 0
    policy_changes_applied: int = 0

    # Tool & environment
    tool_version: str = ""


@dataclass
class Phase3ValidationReceipt(ValidationReceipt):
    """
    Proof that Phase 3 invariants (quality assessment) were checked.

    Records:
      - Sample of recommendations analyzed
      - Quality metrics (confidence, robustness, safety violations)
      - Any bias/confounding issues detected
    """

    phase: str = "phase3"

    # What was analyzed
    recommendations_sampled: int = 0
    recommendations_total: int = 0

    # Quality metrics
    avg_confidence: float = 0.0
    avg_robustness_score: float = 0.0
    safety_violations_found: int = 0
    biases_detected: List[str] = field(default_factory=list)

    # Tool & environment
    tool_version: str = ""


def create_phase1_receipt(
    fixture_path: str,
    fixture_hash: str,
    fixture_episode_count: int,
    checks: Dict[str, bool],
    warnings: List[str],
    failures: List[str],
    tool_version: str = "",
) -> Phase1ValidationReceipt:
    """
    Create and return a Phase 1 validation receipt.

    Args:
        fixture_path: Path to the fixture JSON file
        fixture_hash: SHA256 hash of fixture JSON
        fixture_episode_count: Number of episodes in fixture
        checks: Dict of check_name -> passed
        warnings: List of warning messages
        failures: List of failed check names
        tool_version: Git hash or version string for auditability

    Returns:
        Phase1ValidationReceipt with all fields populated
    """
    return Phase1ValidationReceipt(
        passed=(len(failures) == 0),
        fixture_path=fixture_path,
        fixture_hash=fixture_hash,
        fixture_episode_count=fixture_episode_count,
        checks=checks,
        warnings=warnings,
        failures=failures,
        tool_version=tool_version,
        check_episode_quality=checks.get("episode_quality", False),
        check_recommendations=checks.get("recommendations", False),
        check_stress_gates=checks.get("stress_gates", False),
        check_receipt_chain=checks.get("receipt_chain", False),
    )


def create_phase2_receipt(
    loom_profile: str,
    loom_config_hash: str,
    quintet_config_hash: str,
    checks: Dict[str, bool],
    warnings: List[str],
    failures: List[str],
    quintet_calls_observed: int,
    policy_changes_applied: int,
    tool_version: str = "",
) -> Phase2ValidationReceipt:
    """
    Create and return a Phase 2 validation receipt.

    Args:
        loom_profile: Name of Loom test profile
        loom_config_hash: SHA256 of Loom configuration
        quintet_config_hash: SHA256 of Quintet configuration
        checks: Dict of check_name -> passed
        warnings: List of warning messages
        failures: List of failed check names
        quintet_calls_observed: Count of Quintet API calls during test
        policy_changes_applied: Count of policy changes actually applied
        tool_version: Git hash or version string for auditability

    Returns:
        Phase2ValidationReceipt with all fields populated
    """
    return Phase2ValidationReceipt(
        passed=(len(failures) == 0),
        loom_profile=loom_profile,
        loom_config_hash=loom_config_hash,
        quintet_config_hash=quintet_config_hash,
        checks=checks,
        warnings=warnings,
        failures=failures,
        quintet_calls_observed=quintet_calls_observed,
        policy_changes_applied=policy_changes_applied,
        tool_version=tool_version,
        check_live_path=checks.get("live_path", False),
        check_policy_effect=checks.get("policy_effect", False),
        check_failure_mode=checks.get("failure_mode", False),
    )
