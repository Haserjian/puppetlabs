"""
Policy Change Receipts with Causal & Shadow Experiment Metadata
===============================================================

Pre-registered experiments for safe policy evolution.
Every policy change is an experiment with:
- Target effect + hypothesis
- Required overlap + sample size
- Stress scenarios to validate
- Success criteria + promotion rules

This prevents p-hacking and locks causal + stress expectations together.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any
from datetime import datetime
from enum import Enum
import uuid


class PolicyDomain(str, Enum):
    """Policy domains that can be tuned."""
    TEMPERATURE = "temperature"
    MODEL_SLOT = "model_slot"
    VALIDATION_REGIME = "validation_regime"
    RESOURCE_LIMITS = "resource_limits"
    TIMEOUT_BUDGET = "timeout_budget"
    TREATY_REQUIREMENT = "treaty_requirement"


class InterventionType(str, Enum):
    """Type of policy intervention."""
    PARAMETER_CHANGE = "parameter_change"
    SLOT_DOWNGRADE = "slot_downgrade"
    REGIME_SIMPLIFICATION = "regime_simplification"
    VALIDATION_TIGHTENING = "validation_tightening"
    CONSTRAINT_ADDITION = "constraint_addition"


@dataclass
class SuccessCriteria:
    """Pre-registered success criteria for a policy experiment."""

    # Causal effect requirements
    min_effect_size: float = 0.10
    confidence_level: float = 0.95
    max_ci_width: float = 0.20

    # Data requirements
    min_episodes_per_stratum: int = 30
    min_overlap_per_stratum: float = 0.10

    # Operational requirements
    max_latency_regression_pct: float = 5.0
    max_cost_increase_pct: float = 10.0
    no_new_failure_modes: bool = True

    # Stress requirements
    stress_scenarios_pass: bool = True

    # Validity requirements
    max_validity_concerns: int = 1
    no_unmeasured_confounding_flags: bool = False

    # Duration requirements
    observation_days: int = 7

    details: Optional[Dict[str, Any]] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "min_effect_size": self.min_effect_size,
            "confidence_level": self.confidence_level,
            "max_ci_width": self.max_ci_width,
            "min_episodes_per_stratum": self.min_episodes_per_stratum,
            "min_overlap_per_stratum": self.min_overlap_per_stratum,
            "max_latency_regression_pct": self.max_latency_regression_pct,
            "max_cost_increase_pct": self.max_cost_increase_pct,
            "no_new_failure_modes": self.no_new_failure_modes,
            "stress_scenarios_pass": self.stress_scenarios_pass,
            "max_validity_concerns": self.max_validity_concerns,
            "no_unmeasured_confounding_flags": self.no_unmeasured_confounding_flags,
            "observation_days": self.observation_days,
            "details": self.details or {},
        }


@dataclass
class PolicyIntervention:
    """What changed in a policy."""

    intervention_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    timestamp: datetime = field(default_factory=datetime.utcnow)

    domain: PolicyDomain = PolicyDomain.TEMPERATURE
    intervention_type: InterventionType = InterventionType.PARAMETER_CHANGE

    # What changed
    parameter_name: str = ""
    old_value: Any = None
    new_value: Any = None

    # Why
    hypothesis: str = ""
    mechanism: str = ""

    # Context
    triggered_by: str = ""

    details: Optional[Dict[str, Any]] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "intervention_id": self.intervention_id,
            "timestamp": self.timestamp.isoformat(),
            "domain": self.domain.value,
            "intervention_type": self.intervention_type.value,
            "parameter_name": self.parameter_name,
            "old_value": self.old_value,
            "new_value": self.new_value,
            "hypothesis": self.hypothesis,
            "mechanism": self.mechanism,
            "triggered_by": self.triggered_by,
            "details": self.details or {},
        }


@dataclass
class ShadowExecution:
    """Re-running an episode under a candidate policy."""

    execution_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    timestamp: datetime = field(default_factory=datetime.utcnow)

    # Episode identification
    episode_id: str = ""

    # Actual execution (under current policy)
    actual_success: bool = False
    actual_confidence: float = 0.0
    actual_latency_ms: float = 0.0
    actual_cost: float = 0.0
    actual_errors: List[str] = field(default_factory=list)

    # Shadow execution (under candidate policy)
    shadow_success: bool = False
    shadow_confidence: float = 0.0
    shadow_latency_ms: float = 0.0
    shadow_cost: float = 0.0
    shadow_errors: List[str] = field(default_factory=list)

    # Critical: Was validation regime identical?
    validation_regime_identical: bool = False
    validation_mismatch_reason: str = ""

    # Comparison
    comparable: bool = False
    outcome_changed: bool = False
    confidence_delta: float = 0.0
    latency_delta_pct: float = 0.0
    cost_delta_pct: float = 0.0

    details: Optional[Dict[str, Any]] = field(default_factory=dict)

    def compute_deltas(self) -> None:
        """Compute derived fields."""
        if self.actual_latency_ms > 0:
            self.latency_delta_pct = ((self.shadow_latency_ms - self.actual_latency_ms)
                                       / self.actual_latency_ms * 100)
        if self.actual_cost > 0:
            self.cost_delta_pct = ((self.shadow_cost - self.actual_cost)
                                    / self.actual_cost * 100)
        self.confidence_delta = self.shadow_confidence - self.actual_confidence
        self.outcome_changed = self.actual_success != self.shadow_success
        self.comparable = self.validation_regime_identical

    def to_dict(self) -> Dict[str, Any]:
        return {
            "execution_id": self.execution_id,
            "timestamp": self.timestamp.isoformat(),
            "episode_id": self.episode_id,
            "actual": {
                "success": self.actual_success,
                "confidence": self.actual_confidence,
                "latency_ms": self.actual_latency_ms,
                "cost": self.actual_cost,
                "errors": self.actual_errors,
            },
            "shadow": {
                "success": self.shadow_success,
                "confidence": self.shadow_confidence,
                "latency_ms": self.shadow_latency_ms,
                "cost": self.shadow_cost,
                "errors": self.shadow_errors,
            },
            "validation_regime_identical": self.validation_regime_identical,
            "validation_mismatch_reason": self.validation_mismatch_reason,
            "comparable": self.comparable,
            "outcome_changed": self.outcome_changed,
            "confidence_delta": self.confidence_delta,
            "latency_delta_pct": self.latency_delta_pct,
            "cost_delta_pct": self.cost_delta_pct,
            "details": self.details or {},
        }


@dataclass
class CausalSummary:
    """Causal effect estimate with transparency about validity."""

    summary_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    timestamp: datetime = field(default_factory=datetime.utcnow)

    # Effect estimate
    effect_estimate: float = 0.0
    ci_lower: float = 0.0
    ci_upper: float = 0.0

    # Method
    method: str = "stratified"

    # Data
    sample_size: int = 0
    sample_size_per_stratum_min: int = 0
    sample_size_per_stratum_max: int = 0
    overlap_check_passed: bool = False
    min_overlap_observed: float = 0.0

    # Validity concerns (mandatory transparency)
    validity_concerns: List[str] = field(default_factory=list)

    # Promotion recommendation
    promotion_recommendation: str = "INCONCLUSIVE"

    details: Optional[Dict[str, Any]] = field(default_factory=dict)

    @property
    def has_blocking_concerns(self) -> bool:
        """True if any concern is blocking."""
        blocking_keywords = ["unmeasured_confounding", "severe_heterogeneity"]
        return any(keyword in concern for concern in self.validity_concerns
                   for keyword in blocking_keywords)

    @property
    def ci_contains_zero(self) -> bool:
        """True if 95% CI spans zero (effect not significant)."""
        return self.ci_lower <= 0 <= self.ci_upper

    def to_dict(self) -> Dict[str, Any]:
        return {
            "summary_id": self.summary_id,
            "timestamp": self.timestamp.isoformat(),
            "effect_estimate": self.effect_estimate,
            "ci_95": [self.ci_lower, self.ci_upper],
            "method": self.method,
            "sample_size": self.sample_size,
            "sample_size_per_stratum": {
                "min": self.sample_size_per_stratum_min,
                "max": self.sample_size_per_stratum_max,
            },
            "overlap_check_passed": self.overlap_check_passed,
            "min_overlap_observed": self.min_overlap_observed,
            "validity_concerns": self.validity_concerns,
            "has_blocking_concerns": self.has_blocking_concerns,
            "ci_contains_zero": self.ci_contains_zero,
            "promotion_recommendation": self.promotion_recommendation,
            "details": self.details or {},
        }


@dataclass
class PolicyExperiment:
    """
    Pre-registered policy experiment.

    Defines what we expect to see if a policy change is good,
    what data we need, and what counts as success.
    """

    experiment_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    created_at: datetime = field(default_factory=datetime.utcnow)

    # Identification
    name: str = ""
    description: str = ""

    # The intervention
    intervention: PolicyIntervention = field(default_factory=PolicyIntervention)

    # Pre-registered expectations
    target_effect: float = 0.10
    required_sample_size: int = 30
    success_criteria: SuccessCriteria = field(default_factory=SuccessCriteria)

    # Stress scenarios to validate
    stress_scenarios: List[str] = field(default_factory=list)

    # Duration
    scheduled_duration_days: int = 7
    started_at: Optional[datetime] = None
    ended_at: Optional[datetime] = None

    # Results (populated after experiment completes)
    causal_summary: Optional[CausalSummary] = None
    shadow_executions: List[ShadowExecution] = field(default_factory=list)
    promotion_approved: bool = False
    promotion_approved_by: str = ""
    promotion_approved_at: Optional[datetime] = None

    # Governance
    details: Optional[Dict[str, Any]] = field(default_factory=dict)

    @property
    def is_active(self) -> bool:
        """True if experiment is currently running."""
        return self.started_at is not None and self.ended_at is None

    @property
    def is_complete(self) -> bool:
        """True if experiment has ended."""
        return self.ended_at is not None

    @property
    def promotion_eligible(self) -> bool:
        """True if causal summary recommends promotion."""
        if not self.causal_summary:
            return False
        return self.causal_summary.promotion_recommendation == "PROMOTE"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "experiment_id": self.experiment_id,
            "created_at": self.created_at.isoformat(),
            "name": self.name,
            "description": self.description,
            "intervention": self.intervention.to_dict(),
            "target_effect": self.target_effect,
            "required_sample_size": self.required_sample_size,
            "success_criteria": self.success_criteria.to_dict(),
            "stress_scenarios": self.stress_scenarios,
            "scheduled_duration_days": self.scheduled_duration_days,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "ended_at": self.ended_at.isoformat() if self.ended_at else None,
            "is_active": self.is_active,
            "is_complete": self.is_complete,
            "causal_summary": self.causal_summary.to_dict() if self.causal_summary else None,
            "shadow_executions_count": len(self.shadow_executions),
            "promotion_approved": self.promotion_approved,
            "promotion_approved_by": self.promotion_approved_by,
            "promotion_approved_at": self.promotion_approved_at.isoformat() if self.promotion_approved_at else None,
            "details": self.details or {},
        }


@dataclass
class PolicyChangeReceipt:
    """
    Complete audit trail for a policy change.

    Combines: intervention + shadow executions + causal analysis + promotion decision.
    """

    experiment: PolicyExperiment

    receipt_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    timestamp: datetime = field(default_factory=datetime.utcnow)

    # Outcomes
    promoted: bool = False
    promotion_reason: str = ""

    # Guardian sign-off (if manual)
    guardian_approved: bool = False
    guardian_notes: str = ""

    # Metrics at time of promotion
    metrics_snapshot: Optional[Dict[str, Any]] = None

    details: Optional[Dict[str, Any]] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "receipt_id": self.receipt_id,
            "timestamp": self.timestamp.isoformat(),
            "experiment": self.experiment.to_dict(),
            "promoted": self.promoted,
            "promotion_reason": self.promotion_reason,
            "guardian_approved": self.guardian_approved,
            "guardian_notes": self.guardian_notes,
            "metrics_snapshot": self.metrics_snapshot or {},
            "details": self.details or {},
        }
