"""
Stress Test Promotion Manager
=============================

Manage promotion decisions from shadow (test) to production based on
coverage statistics and eligibility criteria.

Implements the causal loop: stress test -> promotion -> policy update -> validation
"""

from dataclasses import dataclass, field
from typing import Dict, Any, Optional, List
from datetime import datetime
import logging
import copy
import json

from quintet.stress.coverage import CoverageTracker
from quintet.core.types import RESOURCE_LIMITS

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


@dataclass
class PromotionAction:
    """
    Record of a promotion action (promote/constrain/observe/rollback).

    This creates an audit trail of all policy changes made by the stress system.
    """
    scenario_id: str
    decision: PromotionDecision
    action: str  # "promote" | "constrain" | "observe" | "rollback"
    reason: str
    executed_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    result: Optional[Dict[str, Any]] = None  # Details of what changed

    # For rollback capability
    old_policy: Optional[Dict[str, Any]] = None
    new_policy: Optional[Dict[str, Any]] = None

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary."""
        return {
            "scenario_id": self.scenario_id,
            "action": self.action,
            "reason": self.reason,
            "executed_at": self.executed_at,
            "result": self.result,
            "old_policy": self.old_policy,
            "new_policy": self.new_policy,
            "decision": {
                "eligible": self.decision.eligible,
                "confidence_score": self.decision.confidence_score,
                "stats": self.decision.stats
            }
        }


class StressPromotionManager:
    """Manage promotion from shadow (test) to production."""

    def __init__(self, tracker: Optional[CoverageTracker] = None):
        """Initialize promotion manager.

        Args:
            tracker: Optional CoverageTracker instance (creates new if None)
        """
        self.tracker = tracker or CoverageTracker()
        self._logger = logger

        # Audit trail of all promotion actions
        self._promotion_history: List[PromotionAction] = []

        # Policy snapshots for rollback (keyed by scenario_id)
        self._policy_snapshots: Dict[str, Dict[str, Any]] = {}

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

    def execute_promotion(
        self,
        scenario_id: str,
        decision: PromotionDecision,
        policy_changes: Dict[str, Any]
    ) -> PromotionAction:
        """
        Execute a promotion by actually updating RESOURCE_LIMITS.

        Args:
            scenario_id: Scenario being promoted
            decision: PromotionDecision that triggered this
            policy_changes: Dict mapping tier -> {field: new_value}
                Example: {"standard": {"max_wall_time_ms": 60000}}

        Returns:
            PromotionAction with execution details
        """
        # Save snapshot before making changes
        old_policy = self._snapshot_current_policy()
        self._policy_snapshots[scenario_id] = old_policy

        # Apply policy changes
        try:
            for tier, changes in policy_changes.items():
                if tier not in RESOURCE_LIMITS:
                    self._logger.warning(f"Unknown tier '{tier}' in policy_changes")
                    continue

                limits = RESOURCE_LIMITS[tier]
                for field, new_value in changes.items():
                    if not hasattr(limits, field):
                        self._logger.warning(f"Unknown field '{field}' for tier '{tier}'")
                        continue

                    old_value = getattr(limits, field)
                    setattr(limits, field, new_value)
                    self._logger.info(
                        f"Promoted {scenario_id}: {tier}.{field} "
                        f"{old_value} -> {new_value}"
                    )

            new_policy = self._snapshot_current_policy()

            action = PromotionAction(
                scenario_id=scenario_id,
                decision=decision,
                action="promote",
                reason=f"Promoted based on eligibility check (confidence: {decision.confidence_score:.2f})",
                result={"policy_changes": policy_changes},
                old_policy=old_policy,
                new_policy=new_policy
            )

            self._promotion_history.append(action)
            self._logger.info(f"Successfully promoted {scenario_id}")

            return action

        except Exception as e:
            self._logger.error(f"Promotion failed for {scenario_id}: {e}")
            # Rollback on error
            self._restore_policy(old_policy)

            action = PromotionAction(
                scenario_id=scenario_id,
                decision=decision,
                action="rollback",
                reason=f"Promotion failed, rolled back: {str(e)}",
                result={"error": str(e)},
                old_policy=old_policy,
                new_policy=old_policy
            )
            self._promotion_history.append(action)
            raise

    def rollback_promotion(
        self,
        scenario_id: str,
        reason: str
    ) -> PromotionAction:
        """
        Rollback a promotion to previous policy.

        Args:
            scenario_id: Scenario to rollback
            reason: Why we're rolling back

        Returns:
            PromotionAction documenting the rollback
        """
        if scenario_id not in self._policy_snapshots:
            raise ValueError(f"No policy snapshot found for {scenario_id}")

        old_policy = self._policy_snapshots[scenario_id]
        current_policy = self._snapshot_current_policy()

        # Restore the old policy
        self._restore_policy(old_policy)

        # Create a dummy decision for rollback
        decision = PromotionDecision(
            scenario_id=scenario_id,
            eligible=False,
            reason=reason,
            confidence_score=0.0
        )

        action = PromotionAction(
            scenario_id=scenario_id,
            decision=decision,
            action="rollback",
            reason=reason,
            result={"reverted_to": old_policy},
            old_policy=current_policy,
            new_policy=old_policy
        )

        self._promotion_history.append(action)
        self._logger.info(f"Rolled back {scenario_id}: {reason}")

        return action

    def create_regression_scenario(
        self,
        failed_scenario_id: str,
        failure_reason: str
    ) -> Dict[str, Any]:
        """
        Create a new stress scenario to prevent regression.

        When a promotion fails/rolls back, we create a scenario that captures
        the failure mode so we don't promote bad policies again.

        Args:
            failed_scenario_id: Scenario that failed after promotion
            failure_reason: Why it failed

        Returns:
            Dict representing the new regression scenario
        """
        regression_scenario = {
            "scenario_id": f"{failed_scenario_id}_regression",
            "name": f"Regression Prevention: {failed_scenario_id}",
            "description": f"Prevent regression from failed promotion. Original failure: {failure_reason}",
            "category": "regression",
            "domain": "stress_testing",
            "tags": ["regression", "learned_constraint", failed_scenario_id],
            "stress_config": {
                "budget_tiers": ["light", "standard", "deep_search"],
                "timeout_multiplier": 1.5
            },
            "promotion_config": {
                "shadow_mode": True,
                "min_runs": 50,  # Higher bar for regression scenarios
                "max_failure_rate": 0.05  # Much lower tolerance
            },
            "metadata": {
                "created_from_failure": failed_scenario_id,
                "failure_reason": failure_reason,
                "created_at": datetime.utcnow().isoformat()
            }
        }

        self._logger.info(
            f"Created regression scenario: {regression_scenario['scenario_id']}"
        )

        return regression_scenario

    def get_promotion_history(self) -> List[Dict[str, Any]]:
        """Get audit trail of all promotion actions."""
        return [action.to_dict() for action in self._promotion_history]

    def _snapshot_current_policy(self) -> Dict[str, Any]:
        """Snapshot current RESOURCE_LIMITS for rollback."""
        snapshot = {}
        for tier, limits in RESOURCE_LIMITS.items():
            snapshot[tier] = {
                "max_wall_time_ms": limits.max_wall_time_ms,
                "max_plans": limits.max_plans,
                "max_solutions_per_plan": limits.max_solutions_per_plan,
                "max_verification_paths": limits.max_verification_paths,
                "max_memory_mb": limits.max_memory_mb,
                "max_shell_runtime_ms": limits.max_shell_runtime_ms
            }
        return snapshot

    def _restore_policy(self, snapshot: Dict[str, Any]) -> None:
        """Restore RESOURCE_LIMITS from a snapshot."""
        for tier, values in snapshot.items():
            if tier not in RESOURCE_LIMITS:
                continue

            limits = RESOURCE_LIMITS[tier]
            for field, value in values.items():
                if hasattr(limits, field):
                    setattr(limits, field, value)
