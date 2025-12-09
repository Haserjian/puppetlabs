"""
Experiment Registry for Centralized Experiment Management
==========================================================

Thread-safe storage for active experiments, shadow executions, and propensity models.
Manages persistence of experiment data to disk.
"""

from dataclasses import dataclass, asdict
from typing import Dict, List, Optional, Any
from pathlib import Path
import threading
import json
import logging
from datetime import datetime

from quintet.causal.policy_receipts import PolicyExperiment, ShadowExecution

logger = logging.getLogger(__name__)


@dataclass
class ExperimentMetadata:
    """Metadata about an experiment run."""

    experiment_id: str
    created_at: str
    started_at: Optional[str] = None
    ended_at: Optional[str] = None
    shadow_executions_count: int = 0
    episodes_count: int = 0


class ExperimentRegistry:
    """
    Centralized registry for active policy experiments.

    Thread-safe storage for:
    - Active experiments
    - Shadow execution results
    - Propensity score models
    - Stratification mappings

    Persists experiment data to disk in append-only JSONL format.
    """

    def __init__(self, storage_path: str = "logs/experiments/"):
        """
        Initialize registry.

        Args:
            storage_path: Path to store experiment data
        """
        self.storage_path = Path(storage_path)
        self.storage_path.mkdir(parents=True, exist_ok=True)

        self._lock = threading.Lock()
        self._active_experiments: Dict[str, PolicyExperiment] = {}
        self._shadow_executions: Dict[str, List[ShadowExecution]] = {}
        self._metadata: Dict[str, ExperimentMetadata] = {}

        self._logger = logger

    def register_experiment(self, experiment: PolicyExperiment) -> None:
        """
        Register a new experiment.

        Thread-safe. Persists to disk.

        Args:
            experiment: PolicyExperiment to register
        """
        with self._lock:
            self._active_experiments[experiment.experiment_id] = experiment
            self._shadow_executions[experiment.experiment_id] = []

            # Create metadata
            metadata = ExperimentMetadata(
                experiment_id=experiment.experiment_id,
                created_at=datetime.utcnow().isoformat(),
                started_at=experiment.started_at.isoformat() if experiment.started_at else None,
            )
            self._metadata[experiment.experiment_id] = metadata

            # Persist to disk
            self._persist_experiment(experiment)

            self._logger.info(f"Registered experiment: {experiment.experiment_id}")

    def get_active_experiments(self) -> List[PolicyExperiment]:
        """
        Get all currently active experiments.

        Thread-safe.

        Returns:
            List of active PolicyExperiment objects
        """
        with self._lock:
            return [
                e
                for e in self._active_experiments.values()
                if hasattr(e, "is_active") and e.is_active
            ]

    def get_experiment(self, experiment_id: str) -> Optional[PolicyExperiment]:
        """
        Get a specific experiment by ID.

        Thread-safe.

        Args:
            experiment_id: ID of experiment

        Returns:
            PolicyExperiment or None if not found
        """
        with self._lock:
            return self._active_experiments.get(experiment_id)

    def record_shadow_execution(self, experiment_id: str, shadow: ShadowExecution) -> None:
        """
        Record a shadow execution for an experiment.

        Thread-safe. Persists to JSONL append-only file.

        Args:
            experiment_id: ID of experiment
            shadow: ShadowExecution result to record
        """
        with self._lock:
            if experiment_id not in self._shadow_executions:
                self._shadow_executions[experiment_id] = []

            self._shadow_executions[experiment_id].append(shadow)

            # Update metadata
            if experiment_id in self._metadata:
                self._metadata[experiment_id].shadow_executions_count += 1

            # Persist to disk
            self._persist_shadow_execution(experiment_id, shadow)

            self._logger.debug(
                f"Recorded shadow execution {shadow.execution_id} for experiment {experiment_id}"
            )

    def get_shadow_executions(self, experiment_id: str) -> List[ShadowExecution]:
        """
        Get all shadow executions for an experiment.

        Thread-safe.

        Args:
            experiment_id: ID of experiment

        Returns:
            List of ShadowExecution objects
        """
        with self._lock:
            return self._shadow_executions.get(experiment_id, []).copy()

    def get_experiment_data(self, experiment_id: str) -> Dict[str, Any]:
        """
        Get complete data for an experiment (for analysis).

        Thread-safe.

        Args:
            experiment_id: ID of experiment

        Returns:
            Dictionary with experiment, shadows, metadata
        """
        with self._lock:
            experiment = self._active_experiments.get(experiment_id)
            shadows = self._shadow_executions.get(experiment_id, []).copy()
            metadata = self._metadata.get(experiment_id)

        return {
            "experiment": experiment.to_dict() if experiment else None,
            "shadows": [s.to_dict() for s in shadows],
            "metadata": asdict(metadata) if metadata else None,
        }

    def list_experiments(self) -> List[str]:
        """
        List all experiment IDs.

        Thread-safe.

        Returns:
            List of experiment IDs
        """
        with self._lock:
            return list(self._active_experiments.keys())

    def _persist_experiment(self, experiment: PolicyExperiment) -> None:
        """Persist experiment metadata to disk."""
        exp_dir = self.storage_path / experiment.experiment_id
        exp_dir.mkdir(parents=True, exist_ok=True)

        # Write experiment data
        metadata_file = exp_dir / "metadata.json"
        with open(metadata_file, "w") as f:
            json.dump(experiment.to_dict(), f, indent=2, default=str)

        self._logger.debug(f"Persisted experiment metadata to {metadata_file}")

    def _persist_shadow_execution(self, experiment_id: str, shadow: ShadowExecution) -> None:
        """Persist shadow execution to append-only JSONL file."""
        exp_dir = self.storage_path / experiment_id
        exp_dir.mkdir(parents=True, exist_ok=True)

        # Append to shadows.jsonl
        shadows_file = exp_dir / "shadows.jsonl"
        with open(shadows_file, "a") as f:
            json.dump(shadow.to_dict(), f, default=str)
            f.write("\n")

        self._logger.debug(f"Persisted shadow execution to {shadows_file}")

    def load_experiment(self, experiment_id: str) -> Optional[PolicyExperiment]:
        """
        Load experiment from disk.

        Useful for recovering from crashes or loading completed experiments.

        Args:
            experiment_id: ID of experiment

        Returns:
            PolicyExperiment or None if not found
        """
        exp_dir = self.storage_path / experiment_id
        metadata_file = exp_dir / "metadata.json"

        if not metadata_file.exists():
            self._logger.warning(f"Experiment metadata file not found: {metadata_file}")
            return None

        try:
            with open(metadata_file) as f:
                data = json.load(f)

            # Reconstruct PolicyExperiment from dict
            # (Implementation would need from_dict classmethod)
            self._logger.info(f"Loaded experiment from disk: {experiment_id}")
            return data

        except Exception as e:
            self._logger.error(f"Error loading experiment {experiment_id}: {e}")
            return None

    def load_shadow_executions(self, experiment_id: str) -> List[ShadowExecution]:
        """
        Load shadow executions from disk.

        Args:
            experiment_id: ID of experiment

        Returns:
            List of ShadowExecution objects
        """
        exp_dir = self.storage_path / experiment_id
        shadows_file = exp_dir / "shadows.jsonl"

        if not shadows_file.exists():
            return []

        shadows = []
        try:
            with open(shadows_file) as f:
                for line in f:
                    if line.strip():
                        data = json.loads(line)
                        # Reconstruct ShadowExecution from dict
                        # (Implementation would need from_dict classmethod)
                        shadows.append(data)

            self._logger.info(
                f"Loaded {len(shadows)} shadow executions from disk for experiment {experiment_id}"
            )

        except Exception as e:
            self._logger.error(
                f"Error loading shadow executions for {experiment_id}: {e}"
            )

        return shadows


# Global singleton registry
_registry: Optional[ExperimentRegistry] = None
_registry_lock = threading.Lock()


def get_experiment_registry(storage_path: str = "logs/experiments/") -> ExperimentRegistry:
    """
    Get or create global experiment registry.

    Thread-safe singleton.

    Args:
        storage_path: Path to store experiment data (used on first initialization)

    Returns:
        ExperimentRegistry instance
    """
    global _registry

    if _registry is None:
        with _registry_lock:
            if _registry is None:
                _registry = ExperimentRegistry(storage_path)

    return _registry


def reset_registry() -> None:
    """Reset global registry (for testing)."""
    global _registry
    with _registry_lock:
        _registry = None
