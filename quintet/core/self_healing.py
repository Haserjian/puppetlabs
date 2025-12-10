"""
Self-Healing Controller with Hysteresis & Rollback
==================================================

Adjusts policies/slots/temps based on harm/risk signals with:
- State machine: NORMAL → CAUTION → CONSTRAINED → SHADOW_ONLY → BLOCKED
- Hysteresis: separate up/down thresholds + window counts
- Rate limiting: cooldowns prevent thrashing
- Rollback: if tightening doesn't improve, revert to prior state
- Escalation: if stuck in BLOCKED, alert guardian + failsafe to explain-only

Per approved defaults (all thresholds, cooldowns, window counts).
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
from enum import Enum
import uuid


class HealthState(str, Enum):
    """System health states."""
    NORMAL = "normal"
    CAUTION = "caution"
    CONSTRAINED = "constrained"
    SHADOW_ONLY = "shadow_only"
    BLOCKED = "blocked"


@dataclass
class HealthObservation:
    """Single health measurement: harm, error rates, latency, etc."""

    timestamp: datetime = field(default_factory=datetime.utcnow)

    # Key metric: harm probability
    harm_probability: float = 0.0  # 0.0-1.0

    # Supporting metrics
    validation_confidence: float = 0.5
    parse_confidence: float = 0.5
    error_rate: float = 0.0
    latency_ms: float = 0.0
    cost_per_query: float = 0.0

    details: Optional[Dict[str, Any]] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "timestamp": self.timestamp.isoformat(),
            "harm_probability": self.harm_probability,
            "validation_confidence": self.validation_confidence,
            "parse_confidence": self.parse_confidence,
            "error_rate": self.error_rate,
            "latency_ms": self.latency_ms,
            "cost_per_query": self.cost_per_query,
            "details": self.details or {},
        }


@dataclass
class WindowedMetrics:
    """Metrics over a rolling window."""

    window_size_minutes: int = 1
    observations: List[HealthObservation] = field(default_factory=list)

    def add_observation(self, obs: HealthObservation) -> None:
        """Add observation and prune old entries."""
        self.observations.append(obs)
        cutoff = datetime.utcnow() - timedelta(minutes=self.window_size_minutes)
        self.observations = [o for o in self.observations if o.timestamp > cutoff]

    @property
    def harm_probability_ema(self) -> float:
        """Exponential moving average of harm probability."""
        if not self.observations:
            return 0.0
        if len(self.observations) == 1:
            return self.observations[0].harm_probability

        alpha = 0.5
        ema = self.observations[0].harm_probability
        for obs in self.observations[1:]:
            ema = alpha * obs.harm_probability + (1 - alpha) * ema
        return ema

    @property
    def harm_probability_raw(self) -> float:
        """Latest raw harm probability."""
        if not self.observations:
            return 0.0
        return self.observations[-1].harm_probability


@dataclass
class StateTransitionMetadata:
    """Metadata about a state transition."""

    transition_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    timestamp: datetime = field(default_factory=datetime.utcnow)
    from_state: HealthState = HealthState.NORMAL
    to_state: HealthState = HealthState.CAUTION
    trigger_reason: str = ""
    harm_probability: float = 0.0
    windows_breached: int = 0
    observation: Optional[HealthObservation] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "transition_id": self.transition_id,
            "timestamp": self.timestamp.isoformat(),
            "from_state": self.from_state.value,
            "to_state": self.to_state.value,
            "trigger_reason": self.trigger_reason,
            "harm_probability": self.harm_probability,
            "windows_breached": self.windows_breached,
            "observation": self.observation.to_dict() if self.observation else None,
        }


@dataclass
class RollbackMetadata:
    """Metadata about a rollback event."""

    rollback_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    timestamp: datetime = field(default_factory=datetime.utcnow)
    from_state: HealthState = HealthState.CONSTRAINED
    to_state: HealthState = HealthState.CAUTION
    reason: str = ""
    harm_before: float = 0.0
    harm_after: float = 0.0
    improvement_pct: float = 0.0
    windows_observed: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "rollback_id": self.rollback_id,
            "timestamp": self.timestamp.isoformat(),
            "from_state": self.from_state.value,
            "to_state": self.to_state.value,
            "reason": self.reason,
            "harm_before": self.harm_before,
            "harm_after": self.harm_after,
            "improvement_pct": self.improvement_pct,
            "windows_observed": self.windows_observed,
        }


@dataclass
class SelfHealingController:
    """
    Manages policy tightening/relaxing based on system health.

    State machine with hysteresis, rate limiting, and rollback.
    Per-design thresholds, cooldowns, window counts hard-coded.
    """

    controller_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    created_at: datetime = field(default_factory=datetime.utcnow)

    # Current state
    current_state: HealthState = HealthState.NORMAL

    # Metrics tracking
    windowed_metrics: WindowedMetrics = field(default_factory=WindowedMetrics)

    # Hysteresis thresholds (per design defaults)
    # TIGHTENING (easier to tighten)
    threshold_normal_to_caution: float = 0.60
    threshold_caution_to_constrained: float = 0.75
    threshold_constrained_to_shadow_only: float = 0.85
    threshold_shadow_only_to_blocked: float = 0.90
    critical_spike_shadow_only: float = 0.90
    critical_spike_blocked: float = 0.95

    # RELAXING (harder to relax)
    threshold_constrained_to_caution: float = 0.40
    threshold_caution_to_normal: float = 0.30
    threshold_shadow_only_to_constrained: float = 0.70
    threshold_blocked_to_shadow_only: float = 0.70

    # Window counts for breach persistence
    windows_to_tighten_caution: int = 3
    windows_to_tighten_constrained: int = 5
    windows_to_tighten_shadow_only: int = 3
    windows_to_tighten_blocked: int = 3

    windows_to_relax_constrained: int = 8
    windows_to_relax_caution: int = 10
    windows_to_relax_shadow_only: int = 6
    windows_to_relax_blocked: int = 6

    # Cooldowns (minutes)
    cooldown_tighten_minutes: int = 5
    cooldown_relax_minutes: int = 10
    cooldown_blocked_relax_minutes: int = 15

    # Rollback & improvement thresholds
    improvement_threshold: float = 0.15
    rollback_observation_windows: int = 3

    # Escalation
    max_blocked_minutes: int = 30

    # Tracking
    transition_history: List[StateTransitionMetadata] = field(default_factory=list)
    rollback_history: List[RollbackMetadata] = field(default_factory=list)

    # Transition timing
    last_transition_time: Optional[datetime] = None
    transition_count_current_state: int = 0

    # Harm baseline for rollback
    harm_baseline_before_tightening: Optional[float] = None
    windows_since_last_tightening: int = 0

    # Guardian override
    guardian_override_active: bool = False
    guardian_override_until: Optional[datetime] = None
    guardian_override_reason: str = ""

    details: Optional[Dict[str, Any]] = field(default_factory=dict)

    def observe(self, obs: HealthObservation) -> Optional[StateTransitionMetadata]:
        """Observe health, check for state transitions, return transition if occurred."""
        self.windowed_metrics.add_observation(obs)

        # Check for transitions (tightening + relaxing)
        transition = self._check_and_apply_transition(obs)

        # Track time in current state
        if transition:
            self.last_transition_time = datetime.utcnow()
            self.transition_count_current_state = 0
            return transition

        self.transition_count_current_state += 1
        return None

    def _check_and_apply_transition(self, obs: HealthObservation) -> Optional[StateTransitionMetadata]:
        """Check all possible transitions and apply if conditions met."""
        now = datetime.utcnow()

        # Respect cooldown
        if self.last_transition_time:
            if self.current_state in [HealthState.CONSTRAINED, HealthState.CAUTION, HealthState.SHADOW_ONLY]:
                cooldown_delta = timedelta(minutes=self.cooldown_tighten_minutes)
            else:
                cooldown_delta = timedelta(minutes=self.cooldown_relax_minutes)

            if now - self.last_transition_time < cooldown_delta:
                return None

        # Check for critical spikes (bypass window count)
        if obs.harm_probability > self.critical_spike_blocked and self.current_state != HealthState.BLOCKED:
            return self._transition_to(HealthState.BLOCKED, f"Critical spike: hp={obs.harm_probability:.2f}", obs)

        if obs.harm_probability > self.critical_spike_shadow_only and self.current_state in [HealthState.NORMAL, HealthState.CAUTION, HealthState.CONSTRAINED]:
            return self._transition_to(HealthState.SHADOW_ONLY, f"Critical spike: hp={obs.harm_probability:.2f}", obs)

        # Count consecutive breaches for this state's thresholds
        breach_threshold = self._get_breach_threshold(self.current_state, "tighten")
        window_requirement = self._get_window_requirement(self.current_state, "tighten")

        breaches = sum(1 for o in self.windowed_metrics.observations if o.harm_probability > breach_threshold)

        # Try tightening
        if breaches >= window_requirement:
            next_state = self._next_state(self.current_state, "tighten")
            if next_state and next_state != self.current_state:
                self.harm_baseline_before_tightening = self.windowed_metrics.harm_probability_ema
                return self._transition_to(next_state, f"Breach: {breaches}/{window_requirement} windows at hp>{breach_threshold:.2f}", obs)

        # Try relaxing
        relax_threshold = self._get_breach_threshold(self.current_state, "relax")
        relax_window_requirement = self._get_window_requirement(self.current_state, "relax")

        relax_breaches = sum(1 for o in self.windowed_metrics.observations if o.harm_probability > relax_threshold)

        if relax_breaches == 0 and len(self.windowed_metrics.observations) >= relax_window_requirement:
            next_state = self._next_state(self.current_state, "relax")
            if next_state and next_state != self.current_state:
                return self._transition_to(next_state, f"Recovery: {relax_window_requirement} windows at hp<{relax_threshold:.2f}", obs)

        # Check rollback condition (if we recently tightened)
        if self.harm_baseline_before_tightening is not None:
            self.windows_since_last_tightening += 1
            if self.windows_since_last_tightening >= self.rollback_observation_windows:
                improvement = (self.harm_baseline_before_tightening - obs.harm_probability) / max(self.harm_baseline_before_tightening, 0.01)
                if improvement < self.improvement_threshold:
                    return self._perform_rollback(obs, improvement)

        return None

    def _transition_to(self, new_state: HealthState, reason: str, obs: HealthObservation) -> StateTransitionMetadata:
        """Execute a state transition."""
        metadata = StateTransitionMetadata(
            from_state=self.current_state,
            to_state=new_state,
            trigger_reason=reason,
            harm_probability=obs.harm_probability,
            observation=obs,
        )
        self.transition_history.append(metadata)
        self.current_state = new_state
        self.windows_since_last_tightening = 0
        return metadata

    def _perform_rollback(self, obs: HealthObservation, improvement: float) -> Optional[StateTransitionMetadata]:
        """Rollback if improvement is insufficient."""
        if self.harm_baseline_before_tightening is None:
            return None

        prior_state = self._next_state(self.current_state, "relax")
        if prior_state is None or prior_state == self.current_state:
            return None

        improvement_pct = improvement * 100

        rollback_meta = RollbackMetadata(
            from_state=self.current_state,
            to_state=prior_state,
            reason=f"Improvement {improvement_pct:.1f}% < {self.improvement_threshold*100:.0f}% threshold",
            harm_before=self.harm_baseline_before_tightening,
            harm_after=obs.harm_probability,
            improvement_pct=improvement_pct,
            windows_observed=self.windows_since_last_tightening,
        )
        self.rollback_history.append(rollback_meta)

        # Revert state
        transition_meta = StateTransitionMetadata(
            from_state=self.current_state,
            to_state=prior_state,
            trigger_reason=f"Rollback: {rollback_meta.reason}",
            harm_probability=obs.harm_probability,
            observation=obs,
        )
        self.transition_history.append(transition_meta)
        self.current_state = prior_state
        self.harm_baseline_before_tightening = None
        self.windows_since_last_tightening = 0
        return transition_meta

    def _get_breach_threshold(self, state: HealthState, direction: str) -> float:
        """Get harm threshold for breach detection."""
        if direction == "tighten":
            if state == HealthState.NORMAL:
                return self.threshold_normal_to_caution
            elif state == HealthState.CAUTION:
                return self.threshold_caution_to_constrained
            elif state == HealthState.CONSTRAINED:
                return self.threshold_constrained_to_shadow_only
            elif state == HealthState.SHADOW_ONLY:
                return self.threshold_shadow_only_to_blocked
            else:
                return self.threshold_shadow_only_to_blocked
        else:  # relax
            if state == HealthState.CAUTION:
                return self.threshold_constrained_to_caution
            elif state == HealthState.CONSTRAINED:
                return self.threshold_constrained_to_caution
            elif state == HealthState.SHADOW_ONLY:
                return self.threshold_shadow_only_to_constrained
            elif state == HealthState.BLOCKED:
                return self.threshold_blocked_to_shadow_only
            else:
                return 0.0

    def _get_window_requirement(self, state: HealthState, direction: str) -> int:
        """Get required windows for state transition."""
        if direction == "tighten":
            if state == HealthState.NORMAL:
                return self.windows_to_tighten_caution
            elif state == HealthState.CAUTION:
                return self.windows_to_tighten_constrained
            elif state == HealthState.CONSTRAINED:
                return self.windows_to_tighten_shadow_only
            else:
                return self.windows_to_tighten_blocked
        else:  # relax
            if state == HealthState.CAUTION:
                return self.windows_to_relax_caution
            elif state == HealthState.CONSTRAINED:
                return self.windows_to_relax_constrained
            elif state == HealthState.SHADOW_ONLY:
                return self.windows_to_relax_shadow_only
            elif state == HealthState.BLOCKED:
                return self.windows_to_relax_blocked
            else:
                return 1

    def _next_state(self, current: HealthState, direction: str) -> Optional[HealthState]:
        """Get next state in transition direction."""
        if direction == "tighten":
            mapping = {
                HealthState.NORMAL: HealthState.CAUTION,
                HealthState.CAUTION: HealthState.CONSTRAINED,
                HealthState.CONSTRAINED: HealthState.SHADOW_ONLY,
                HealthState.SHADOW_ONLY: HealthState.BLOCKED,
                HealthState.BLOCKED: None,
            }
        else:  # relax
            mapping = {
                HealthState.BLOCKED: HealthState.SHADOW_ONLY,
                HealthState.SHADOW_ONLY: HealthState.CONSTRAINED,
                HealthState.CONSTRAINED: HealthState.CAUTION,
                HealthState.CAUTION: HealthState.NORMAL,
                HealthState.NORMAL: None,
            }
        return mapping.get(current)

    def get_current_policy(self) -> Dict[str, Any]:
        """Get policy adjustments for current state."""
        policies = {
            HealthState.NORMAL: {
                "state": "normal",
                "temperature_cap": 1.0,
                "model_slot": "default",
                "validation_regime": "full",
                "requires_guardian_approval": False,
            },
            HealthState.CAUTION: {
                "state": "caution",
                "temperature_cap": 0.8,
                "model_slot": "safe",
                "validation_regime": "full",
                "requires_guardian_approval": False,
            },
            HealthState.CONSTRAINED: {
                "state": "constrained",
                "temperature_cap": 0.5,
                "model_slot": "conservative",
                "validation_regime": "strict",
                "requires_guardian_approval": True,
            },
            HealthState.SHADOW_ONLY: {
                "state": "shadow_only",
                "temperature_cap": 0.3,
                "model_slot": "minimal",
                "validation_regime": "exhaustive",
                "requires_guardian_approval": True,
                "force_explain_only": True,
            },
            HealthState.BLOCKED: {
                "state": "blocked",
                "temperature_cap": 0.1,
                "model_slot": "none",
                "validation_regime": "explain_only",
                "requires_guardian_approval": True,
                "block_all_new_queries": True,
            },
        }
        return policies.get(self.current_state, policies[HealthState.NORMAL])

    def to_dict(self) -> Dict[str, Any]:
        return {
            "controller_id": self.controller_id,
            "current_state": self.current_state.value,
            "transition_count": len(self.transition_history),
            "rollback_count": len(self.rollback_history),
            "last_transition_time": self.last_transition_time.isoformat() if self.last_transition_time else None,
            "latest_harm": self.windowed_metrics.harm_probability_raw,
            "latest_harm_ema": self.windowed_metrics.harm_probability_ema,
        }


# Singleton instance
_controller_instance: Optional[SelfHealingController] = None


def get_self_healing_controller() -> SelfHealingController:
    """Get or create the global self-healing controller."""
    global _controller_instance
    if _controller_instance is None:
        _controller_instance = SelfHealingController(
            windowed_metrics=WindowedMetrics(window_size_minutes=1),
        )
    return _controller_instance
