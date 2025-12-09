"""
Stress Testing Scenario Definitions
====================================

YAML-based scenario definitions for systematic edge case testing,
budget sweeps, and tolerance analysis.
"""

from dataclasses import dataclass, field, asdict
from typing import Dict, List, Any, Optional
from pathlib import Path
import yaml
import json
import logging

logger = logging.getLogger(__name__)


@dataclass
class StressScenario:
    """Declarative stress testing scenario."""

    scenario_id: str
    name: str
    description: str
    category: str  # "edge_cases" | "budget_sweep" | "tolerance_analysis"
    domain: str    # "algebra" | "calculus" | "statistics" | etc.
    tags: List[str] = field(default_factory=list)
    stress_config: Dict[str, Any] = field(default_factory=dict)
    edge_cases: List[Dict[str, Any]] = field(default_factory=list)
    promotion_config: Optional[Dict[str, Any]] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return asdict(self)

    def to_json(self) -> str:
        """Convert to JSON string."""
        return json.dumps(self.to_dict(), indent=2, default=str)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "StressScenario":
        """Create from dictionary (e.g., from YAML)."""
        return cls(**data)

    @classmethod
    def from_yaml(cls, path: str) -> "StressScenario":
        """Load scenario from YAML file.

        Args:
            path: Path to YAML scenario file

        Returns:
            StressScenario instance
        """
        yaml_path = Path(path)
        if not yaml_path.exists():
            raise FileNotFoundError(f"Scenario file not found: {yaml_path}")

        try:
            with open(yaml_path) as f:
                data = yaml.safe_load(f)

            logger.info(f"Loaded stress scenario from {yaml_path}: {data.get('scenario_id')}")
            return cls.from_dict(data)

        except yaml.YAMLError as e:
            logger.error(f"Error parsing YAML file {yaml_path}: {e}")
            raise
        except Exception as e:
            logger.error(f"Error loading scenario from {yaml_path}: {e}")
            raise

    def get_edge_cases(self, category: Optional[str] = None) -> List[Dict[str, Any]]:
        """Get edge cases, optionally filtered by category.

        Args:
            category: Optional category filter (e.g., "overflow")

        Returns:
            List of edge case dictionaries
        """
        if category is None:
            return self.edge_cases

        return [
            case for case in self.edge_cases
            if case.get("category") == category
        ]

    def get_budget_tiers(self) -> List[str]:
        """Get budget tiers from stress config.

        Returns:
            List of tier names (e.g., ["light", "standard", "deep_search"])
        """
        budget_config = self.stress_config.get("budget_tiers", [])
        if isinstance(budget_config, list):
            return [tier.get("tier", "standard") for tier in budget_config]
        return ["standard"]

    def get_tolerance_sweep(self) -> Dict[str, List[float]]:
        """Get tolerance sweep parameters.

        Returns:
            Dictionary with "absolute" and "relative" tolerance ranges
        """
        sweep = self.stress_config.get("tolerance_sweep", {})
        return {
            "absolute": sweep.get("absolute", [1e-9, 1e-6]),
            "relative": sweep.get("relative", [1e-6, 1e-3])
        }

    def get_expected_behavior(self) -> Dict[str, Any]:
        """Get expected behavior specification.

        Returns:
            Dictionary with expected outcomes and thresholds
        """
        return self.stress_config.get("expected_behavior", {})

    def is_promotion_enabled(self) -> bool:
        """Check if promotion is enabled for this scenario.

        Returns:
            True if promotion_config exists and shadow_mode is true
        """
        if not self.promotion_config:
            return False
        return self.promotion_config.get("shadow_mode", False)

    def get_promotion_criteria(self) -> Dict[str, Any]:
        """Get promotion eligibility criteria.

        Returns:
            Dictionary with min_runs, max_failure_rate, min_avg_confidence
        """
        if not self.promotion_config:
            return {
                "min_runs": 20,
                "max_failure_rate": 0.15,
                "min_avg_confidence": 0.6
            }

        criteria = self.promotion_config.get("promotion_criteria", {})
        return {
            "min_runs": criteria.get("min_runs", 20),
            "max_failure_rate": criteria.get("max_failure_rate", 0.15),
            "min_avg_confidence": criteria.get("min_avg_confidence", 0.6)
        }
