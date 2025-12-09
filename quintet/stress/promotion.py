"""
Stress Test Promotion Manager
=============================

Manage promotion decisions from shadow (test) to production based on
coverage statistics and eligibility criteria.
"""

from dataclasses import dataclass, field
from typing import Dict, Any, Optional
import logging

from quintet.stress.coverage import CoverageTracker

logger = logging.getLogger(__name__)


@dataclass
class PromotionDecision:
    """Promotion eligibility decision."""

    scenario_id: str
    eligible: bool
    reason: str
    stats: Dict[str, Any] = field(default_factory=dict)
    confidence_score: float = 0.0
    checks_passed: Dict[str, bool] = field(default_factory=dict)


class StressPromotionManager:
    """Manage promotion from shadow (test) to production."""

    def __init__(self, tracker: Optional[CoverageTracker] = None):
        """Initialize promotion manager.

        Args:
            tracker: Optional CoverageTracker instance (creates new if None)
        """
        self.tracker = tracker or CoverageTracker()
        self._logger = logger

    def check_promotion_eligibility(
        self,
        scenario_id: str,
        min_runs: Optional[int] = None,
        max_failure_rate: Optional[float] = None,
        min_avg_confidence: Optional[float] = None
    ) -> PromotionDecision:
        """Check if scenario is eligible for promotion.

        Args:
            scenario_id: Scenario identifier
            min_runs: Minimum number of test runs (default: 20)
            max_failure_rate: Maximum acceptable failure rate (default: 0.15)
            min_avg_confidence: Minimum average confidence (default: 0.60)

        Returns:
            PromotionDecision with eligibility and reasoning
        """
        # Use defaults
        min_runs = min_runs or 20
        max_failure_rate = max_failure_rate or 0.15
        min_avg_confidence = min_avg_confidence or 0.60

        # Get scenario stats
        stats = self.tracker.get_scenario_stats(scenario_id)

        checks_passed = {}
        reasons = []

        # Check 1: Minimum runs
        check1 = stats["total_runs"] >= min_runs
        checks_passed["min_runs"] = check1
        if not check1:
            reasons.append(
                f"Insufficient runs: {stats['total_runs']} < {min_runs} required"
            )
        else:
            reasons.append(f"✓ Runs threshold met: {stats['total_runs']} >= {min_runs}")

        # Check 2: Failure rate
        failure_rate = stats["failure_rate"]
        check2 = failure_rate <= max_failure_rate
        checks_passed["failure_rate"] = check2
        if not check2:
            reasons.append(
                f"Failure rate too high: {failure_rate:.1%} > {max_failure_rate:.1%}"
            )
        else:
            reasons.append(f"✓ Failure rate acceptable: {failure_rate:.1%} <= {max_failure_rate:.1%}")

        # Check 3: Average confidence
        avg_conf = stats["avg_confidence"]
        check3 = avg_conf >= min_avg_confidence
        checks_passed["avg_confidence"] = check3
        if not check3:
            reasons.append(
                f"Confidence too low: {avg_conf:.2f} < {min_avg_confidence:.2f}"
            )
        else:
            reasons.append(f"✓ Confidence threshold met: {avg_conf:.2f} >= {min_avg_confidence:.2f}")

        # Overall eligibility
        eligible = check1 and check2 and check3

        # Compute confidence score (0-1) for promotion likelihood
        confidence_score = self._compute_confidence_score(
            stats, min_runs, max_failure_rate, min_avg_confidence
        )

        decision = PromotionDecision(
            scenario_id=scenario_id,
            eligible=eligible,
            reason="\n".join(reasons),
            stats=stats,
            confidence_score=confidence_score,
            checks_passed=checks_passed
        )

        self._logger.info(
            f"Promotion eligibility check: {scenario_id} - eligible={eligible}, "
            f"confidence={confidence_score:.2f}"
        )

        return decision

    def _compute_confidence_score(
        self,
        stats: Dict[str, Any],
        min_runs: int,
        max_failure_rate: float,
        min_avg_confidence: float
    ) -> float:
        """Compute a confidence score for promotion.

        Args:
            stats: Scenario statistics
            min_runs: Minimum runs threshold
            max_failure_rate: Maximum failure rate threshold
            min_avg_confidence: Minimum confidence threshold

        Returns:
            Confidence score from 0.0 to 1.0
        """
        components = []

        # 1. Runs completeness (0-1)
        runs_complete = min(stats["total_runs"] / min_runs, 1.0)
        components.append(runs_complete)

        # 2. Failure rate margin (0-1)
        # How much margin between current and threshold?
        current_fr = stats["failure_rate"]
        if current_fr <= max_failure_rate:
            margin = (max_failure_rate - current_fr) / max_failure_rate
            components.append(min(margin * 1.5, 1.0))  # Scale up margin bonus
        else:
            components.append(0.0)

        # 3. Confidence margin (0-1)
        # How much above threshold?
        current_conf = stats["avg_confidence"]
        if current_conf >= min_avg_confidence:
            margin = (current_conf - min_avg_confidence) / (1.0 - min_avg_confidence)
            components.append(min(margin, 1.0))
        else:
            components.append(0.0)

        # Weighted average: 40% runs, 30% failure rate, 30% confidence
        score = (
            0.4 * components[0] +
            0.3 * components[1] +
            0.3 * components[2]
        )

        return max(0.0, min(1.0, score))

    def get_promotion_summary(self) -> Dict[str, Any]:
        """Get summary of promotion readiness across all scenarios.

        Returns:
            Dictionary with promotion readiness by status
        """
        report = self.tracker.generate_coverage_report()

        eligible_scenarios = []
        near_eligible_scenarios = []
        not_eligible_scenarios = []

        for scenario in report.get("scenarios", []):
            decision = self.check_promotion_eligibility(scenario["scenario_id"])

            if decision.eligible:
                eligible_scenarios.append({
                    "scenario_id": scenario["scenario_id"],
                    "name": scenario.get("name"),
                    "confidence_score": decision.confidence_score
                })
            elif decision.confidence_score >= 0.5:
                near_eligible_scenarios.append({
                    "scenario_id": scenario["scenario_id"],
                    "name": scenario.get("name"),
                    "confidence_score": decision.confidence_score,
                    "missing_checks": [k for k, v in decision.checks_passed.items() if not v]
                })
            else:
                not_eligible_scenarios.append({
                    "scenario_id": scenario["scenario_id"],
                    "name": scenario.get("name"),
                    "confidence_score": decision.confidence_score
                })

        return {
            "ready_for_promotion": eligible_scenarios,
            "near_promotion_ready": near_eligible_scenarios,
            "not_ready": not_eligible_scenarios,
            "total_scenarios": len(report.get("scenarios", [])),
            "promotion_ready_pct": len(eligible_scenarios) / max(len(report.get("scenarios", [])), 1)
        }
