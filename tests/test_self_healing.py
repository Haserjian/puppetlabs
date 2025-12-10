"""
Tests for SelfHealingController: state machine, hysteresis, rollback, escalation.
"""

import pytest
from datetime import datetime, timedelta
from quintet.core.self_healing import (
    SelfHealingController, HealthObservation, HealthState, WindowedMetrics,
    get_self_healing_controller,
)


class TestHealthObservation:
    """Health metrics observation."""

    def test_observation_creation(self):
        """Create a health observation."""
        obs = HealthObservation(
            harm_probability=0.5,
            validation_confidence=0.8,
            error_rate=0.02,
        )
        assert obs.harm_probability == 0.5
        assert obs.validation_confidence == 0.8
        assert obs.error_rate == 0.02

    def test_observation_serialization(self):
        """Observation to_dict."""
        obs = HealthObservation(harm_probability=0.5)
        d = obs.to_dict()
        assert d["harm_probability"] == 0.5
        assert "timestamp" in d


class TestWindowedMetrics:
    """Windowed metrics with EMA smoothing."""

    def test_windowed_metrics_ema(self):
        """EMA smooths rapid changes."""
        wm = WindowedMetrics(window_size_minutes=10)
        obs1 = HealthObservation(harm_probability=0.3)
        wm.add_observation(obs1)
        ema1 = wm.harm_probability_ema
        assert ema1 == 0.3

        obs2 = HealthObservation(harm_probability=0.9)
        obs2.timestamp = datetime.utcnow()
        wm.add_observation(obs2)
        ema2 = wm.harm_probability_ema

        # EMA between 0.3 and 0.9
        assert ema1 < ema2 < 0.9


class TestStateTransitions:
    """State machine transitions."""

    def test_normal_to_caution(self):
        """NORMAL → CAUTION: 3 windows above 0.60."""
        controller = SelfHealingController()

        for i in range(3):
            obs = HealthObservation(harm_probability=0.65)
            trans = controller.observe(obs)

        assert controller.current_state == HealthState.CAUTION
        assert len(controller.transition_history) == 1

    def test_caution_to_constrained(self):
        """CAUTION → CONSTRAINED: 5 windows above 0.75."""
        controller = SelfHealingController()
        controller.current_state = HealthState.CAUTION
        controller.last_transition_time = datetime.utcnow() - timedelta(minutes=10)

        for i in range(5):
            obs = HealthObservation(harm_probability=0.80)
            trans = controller.observe(obs)

        assert controller.current_state == HealthState.CONSTRAINED

    def test_critical_spike_bypass(self):
        """Critical spike bypasses window count."""
        controller = SelfHealingController()

        # Spike to SHADOW_ONLY (0.92 > 0.90)
        obs = HealthObservation(harm_probability=0.92)
        trans = controller.observe(obs)

        assert trans is not None
        assert controller.current_state == HealthState.SHADOW_ONLY

    def test_cooldown_prevents_thrashing(self):
        """Cooldown blocks rapid transitions."""
        controller = SelfHealingController()

        # First transition to CAUTION
        for i in range(3):
            obs = HealthObservation(harm_probability=0.65)
            controller.observe(obs)

        assert controller.current_state == HealthState.CAUTION

        # Try immediate re-transition (blocked by cooldown)
        for i in range(5):
            obs = HealthObservation(harm_probability=0.78)
            trans = controller.observe(obs)
            assert trans is None

        assert controller.current_state == HealthState.CAUTION


class TestRelaxation:
    """Relaxing constraints (harder than tightening)."""

    def test_caution_to_normal_recovery(self):
        """CAUTION → NORMAL: 10 windows below 0.30."""
        controller = SelfHealingController()
        controller.current_state = HealthState.CAUTION
        controller.last_transition_time = datetime.utcnow() - timedelta(minutes=20)

        for i in range(10):
            obs = HealthObservation(harm_probability=0.20)
            trans = controller.observe(obs)

        assert controller.current_state == HealthState.NORMAL

    def test_shadow_only_to_constrained(self):
        """SHADOW_ONLY → CONSTRAINED: 6 windows below 0.70."""
        controller = SelfHealingController()
        controller.current_state = HealthState.SHADOW_ONLY
        controller.last_transition_time = datetime.utcnow() - timedelta(minutes=20)

        for i in range(6):
            obs = HealthObservation(harm_probability=0.60)
            trans = controller.observe(obs)

        assert controller.current_state == HealthState.CONSTRAINED


class TestRollback:
    """Rollback when tightening doesn't improve."""

    def test_rollback_insufficient_improvement(self):
        """Rollback if improvement < 15% after 3 windows."""
        controller = SelfHealingController()
        controller.current_state = HealthState.CAUTION
        controller.last_transition_time = datetime.utcnow() - timedelta(minutes=20)

        # Tighten to CONSTRAINED with baseline ~0.78
        for i in range(5):
            obs = HealthObservation(harm_probability=0.78)
            controller.observe(obs)

        assert controller.current_state == HealthState.CONSTRAINED
        baseline = controller.harm_baseline_before_tightening
        assert baseline is not None

        # Reset for rollback
        controller.last_transition_time = datetime.utcnow() - timedelta(minutes=10)

        # After 3 windows at 0.75 (3.8% improvement < 15%)
        for i in range(3):
            obs = HealthObservation(harm_probability=0.75)
            trans = controller.observe(obs)

        assert controller.current_state == HealthState.CAUTION
        assert len(controller.rollback_history) == 1

    def test_no_rollback_good_improvement(self):
        """No rollback if improvement >= 15%."""
        controller = SelfHealingController()
        controller.current_state = HealthState.CAUTION
        controller.last_transition_time = datetime.utcnow() - timedelta(minutes=20)

        for i in range(5):
            obs = HealthObservation(harm_probability=0.78)
            controller.observe(obs)

        baseline = controller.harm_baseline_before_tightening
        controller.last_transition_time = datetime.utcnow() - timedelta(minutes=10)

        # After 3 windows at 0.65 (16.7% improvement > 15%)
        for i in range(3):
            obs = HealthObservation(harm_probability=0.65)
            trans = controller.observe(obs)

        assert controller.current_state == HealthState.CONSTRAINED
        assert len(controller.rollback_history) == 0


class TestPolicies:
    """State-dependent policies."""

    def test_normal_state_policy(self):
        """NORMAL state has full permissions."""
        controller = SelfHealingController()
        policy = controller.get_current_policy()

        assert policy["state"] == "normal"
        assert policy["temperature_cap"] == 1.0
        assert not policy["requires_guardian_approval"]

    def test_shadow_only_policy(self):
        """SHADOW_ONLY state has restrictions."""
        controller = SelfHealingController()
        controller.current_state = HealthState.SHADOW_ONLY

        policy = controller.get_current_policy()
        assert policy["state"] == "shadow_only"
        assert policy["temperature_cap"] == 0.3
        assert policy["requires_guardian_approval"] is True
        assert policy["force_explain_only"] is True

    def test_blocked_state_policy(self):
        """BLOCKED state blocks all queries."""
        controller = SelfHealingController()
        controller.current_state = HealthState.BLOCKED

        policy = controller.get_current_policy()
        assert policy["state"] == "blocked"
        assert policy["block_all_new_queries"] is True
        assert policy["requires_guardian_approval"] is True


class TestSingleton:
    """Global controller singleton."""

    def test_singleton_instance(self):
        """Singleton returns same instance."""
        ctrl1 = get_self_healing_controller()
        ctrl2 = get_self_healing_controller()
        assert ctrl1 is ctrl2


class TestSerialization:
    """Serialization and audit trails."""

    def test_controller_serialization(self):
        """Controller to_dict."""
        controller = SelfHealingController()
        d = controller.to_dict()
        assert d["current_state"] == "normal"
        assert "controller_id" in d
        assert "transition_count" in d

    def test_transition_metadata(self):
        """Transition metadata tracks details."""
        controller = SelfHealingController()
        for i in range(3):
            obs = HealthObservation(harm_probability=0.65)
            trans = controller.observe(obs)

        assert len(controller.transition_history) == 1
        meta = controller.transition_history[0]
        assert meta.from_state == HealthState.NORMAL
        assert meta.to_state == HealthState.CAUTION
        assert "Breach" in meta.trigger_reason

    def test_rollback_metadata(self):
        """Rollback metadata tracks details."""
        controller = SelfHealingController()
        controller.current_state = HealthState.CAUTION
        controller.last_transition_time = datetime.utcnow() - timedelta(minutes=20)

        for i in range(5):
            controller.observe(HealthObservation(harm_probability=0.78))

        controller.last_transition_time = datetime.utcnow() - timedelta(minutes=10)
        for i in range(3):
            controller.observe(HealthObservation(harm_probability=0.75))

        assert len(controller.rollback_history) == 1
        meta = controller.rollback_history[0]
        assert meta.from_state == HealthState.CONSTRAINED
        assert meta.to_state == HealthState.CAUTION
        assert "Improvement" in meta.reason
