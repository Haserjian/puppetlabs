"""
Tests for policy receipts: PolicyExperiment, PolicyIntervention, ShadowExecution, CausalSummary.
"""

import pytest
from datetime import datetime, timedelta
from quintet.causal.policy_receipts import (
    PolicyDomain, InterventionType, SuccessCriteria, PolicyIntervention,
    ShadowExecution, CausalSummary, PolicyExperiment, PolicyChangeReceipt,
)


class TestPolicyIntervention:
    """Policy intervention: what changed."""

    def test_intervention_creation(self):
        """Create an intervention."""
        pi = PolicyIntervention(
            domain=PolicyDomain.TEMPERATURE,
            intervention_type=InterventionType.PARAMETER_CHANGE,
            parameter_name="temperature",
            old_value=0.8,
            new_value=0.5,
            hypothesis="Lower temp → higher validation confidence",
        )
        assert pi.domain == PolicyDomain.TEMPERATURE
        assert pi.parameter_name == "temperature"
        assert pi.old_value == 0.8
        assert pi.new_value == 0.5

    def test_intervention_serialization(self):
        """Intervention to_dict."""
        pi = PolicyIntervention(
            parameter_name="temperature",
            old_value=0.8,
            new_value=0.5,
        )
        d = pi.to_dict()
        assert d["parameter_name"] == "temperature"
        assert d["old_value"] == 0.8
        assert d["new_value"] == 0.5
        assert "intervention_id" in d
        assert "timestamp" in d


class TestShadowExecution:
    """Shadow execution: re-running under candidate policy."""

    def test_shadow_creation(self):
        """Create a shadow execution."""
        se = ShadowExecution(
            episode_id="ep_001",
            actual_success=True,
            actual_confidence=0.8,
            actual_latency_ms=100.0,
            actual_cost=0.05,
            shadow_success=True,
            shadow_confidence=0.85,
            shadow_latency_ms=105.0,
            shadow_cost=0.06,
            validation_regime_identical=True,
        )
        se.compute_deltas()

        assert se.comparable
        assert se.confidence_delta == pytest.approx(0.05)
        assert se.latency_delta_pct == pytest.approx(5.0)
        assert se.cost_delta_pct == pytest.approx(20.0)
        assert not se.outcome_changed

    def test_shadow_incomparable_regimes(self):
        """Shadow execution with different validation regimes."""
        se = ShadowExecution(
            episode_id="ep_001",
            actual_success=True,
            actual_confidence=0.8,
            shadow_success=True,
            shadow_confidence=0.9,
            validation_regime_identical=False,
            validation_mismatch_reason="actual used symbolic, shadow used numeric only",
        )
        se.compute_deltas()

        assert not se.comparable
        assert se.validation_mismatch_reason

    def test_shadow_outcome_changed(self):
        """Shadow execution: outcome flipped."""
        se = ShadowExecution(
            episode_id="ep_001",
            actual_success=True,
            shadow_success=False,
            validation_regime_identical=True,
        )
        se.compute_deltas()

        assert se.outcome_changed
        assert se.comparable

    def test_shadow_serialization(self):
        """Shadow execution to_dict."""
        se = ShadowExecution(
            episode_id="ep_001",
            actual_success=True,
            actual_confidence=0.8,
            shadow_success=True,
            shadow_confidence=0.85,
            validation_regime_identical=True,
        )
        se.compute_deltas()
        d = se.to_dict()

        assert d["episode_id"] == "ep_001"
        assert d["actual"]["success"] is True
        assert d["shadow"]["success"] is True
        assert d["comparable"] is True


class TestCausalSummary:
    """Causal effect estimate with validity concerns."""

    def test_causal_summary_clean(self):
        """Causal summary: positive effect, no concerns."""
        cs = CausalSummary(
            effect_estimate=0.12,
            ci_lower=0.05,
            ci_upper=0.19,
            method="stratified",
            sample_size=150,
            overlap_check_passed=True,
            min_overlap_observed=0.15,
            validity_concerns=[],
            promotion_recommendation="PROMOTE",
        )
        assert not cs.ci_contains_zero
        assert not cs.has_blocking_concerns
        assert cs.promotion_recommendation == "PROMOTE"

    def test_causal_summary_ci_spans_zero(self):
        """Causal summary: effect uncertain (CI spans zero)."""
        cs = CausalSummary(
            effect_estimate=0.02,
            ci_lower=-0.05,
            ci_upper=0.09,
            method="stratified",
            sample_size=50,
            validity_concerns=["insufficient_sample_size"],
            promotion_recommendation="HOLD",
        )
        assert cs.ci_contains_zero
        assert not cs.has_blocking_concerns

    def test_causal_summary_with_concerns(self):
        """Causal summary: valid effect but with concerns."""
        cs = CausalSummary(
            effect_estimate=0.15,
            ci_lower=0.08,
            ci_upper=0.22,
            method="stratified",
            sample_size=100,
            validity_concerns=[
                "high_heterogeneity: effect differs 2.5x across domains",
                "aging_estimates: data median age 25 days",
            ],
            promotion_recommendation="PROMOTE",
        )
        assert not cs.ci_contains_zero
        assert not cs.has_blocking_concerns

    def test_causal_summary_blocking_concern(self):
        """Causal summary: blocking concern detected."""
        cs = CausalSummary(
            effect_estimate=0.12,
            ci_lower=0.05,
            ci_upper=0.19,
            method="stratified",
            sample_size=100,
            validity_concerns=[
                "unmeasured_confounding: user_skill not logged",
            ],
            promotion_recommendation="INVESTIGATE",
        )
        assert cs.has_blocking_concerns

    def test_causal_summary_serialization(self):
        """Causal summary to_dict."""
        cs = CausalSummary(
            effect_estimate=0.12,
            ci_lower=0.05,
            ci_upper=0.19,
            sample_size=150,
        )
        d = cs.to_dict()
        assert d["effect_estimate"] == 0.12
        assert d["ci_95"] == [0.05, 0.19]
        assert d["sample_size"] == 150


class TestSuccessCriteria:
    """Pre-registered success criteria."""

    def test_success_criteria_defaults(self):
        """Success criteria with defaults."""
        sc = SuccessCriteria()
        assert sc.min_effect_size == 0.10
        assert sc.min_episodes_per_stratum == 30
        assert sc.min_overlap_per_stratum == 0.10
        assert sc.observation_days == 7

    def test_success_criteria_custom(self):
        """Success criteria with custom values."""
        sc = SuccessCriteria(
            min_effect_size=0.20,
            min_episodes_per_stratum=50,
            observation_days=14,
        )
        assert sc.min_effect_size == 0.20
        assert sc.min_episodes_per_stratum == 50
        assert sc.observation_days == 14

    def test_success_criteria_serialization(self):
        """Success criteria to_dict."""
        sc = SuccessCriteria(min_effect_size=0.15)
        d = sc.to_dict()
        assert d["min_effect_size"] == 0.15


class TestPolicyExperiment:
    """Pre-registered policy experiment."""

    def test_experiment_creation(self):
        """Create a policy experiment."""
        intervention = PolicyIntervention(
            parameter_name="temperature",
            old_value=0.8,
            new_value=0.5,
        )
        pe = PolicyExperiment(
            name="Lower temperature in safety-critical math",
            intervention=intervention,
            target_effect=0.10,
            required_sample_size=30,
            stress_scenarios=["healthcare_low_confidence", "timeout_risk"],
        )
        assert pe.name == "Lower temperature in safety-critical math"
        assert pe.target_effect == 0.10
        assert len(pe.stress_scenarios) == 2

    def test_experiment_active_status(self):
        """Experiment active/complete status."""
        pe = PolicyExperiment(name="test")

        # Not started
        assert not pe.is_active
        assert not pe.is_complete

        # Started
        pe.started_at = datetime.utcnow()
        assert pe.is_active
        assert not pe.is_complete

        # Ended
        pe.ended_at = datetime.utcnow()
        assert not pe.is_active
        assert pe.is_complete

    def test_experiment_promotion_eligible(self):
        """Experiment promotion eligibility."""
        pe = PolicyExperiment(name="test")

        # No causal summary yet
        assert not pe.promotion_eligible

        # Causal summary says PROMOTE
        cs = CausalSummary(
            promotion_recommendation="PROMOTE",
        )
        pe.causal_summary = cs
        assert pe.promotion_eligible

        # Causal summary says HOLD
        cs_hold = CausalSummary(
            promotion_recommendation="HOLD",
        )
        pe.causal_summary = cs_hold
        assert not pe.promotion_eligible

    def test_experiment_serialization(self):
        """Experiment to_dict."""
        intervention = PolicyIntervention(parameter_name="temperature")
        pe = PolicyExperiment(
            name="test_experiment",
            intervention=intervention,
            target_effect=0.10,
        )
        d = pe.to_dict()

        assert d["name"] == "test_experiment"
        assert d["target_effect"] == 0.10
        assert "experiment_id" in d
        assert "intervention" in d


class TestPolicyChangeReceipt:
    """Complete policy change audit trail."""

    def test_receipt_creation(self):
        """Create a policy change receipt."""
        intervention = PolicyIntervention(parameter_name="temperature")
        pe = PolicyExperiment(name="test", intervention=intervention)
        cs = CausalSummary(promotion_recommendation="PROMOTE")
        pe.causal_summary = cs

        receipt = PolicyChangeReceipt(
            experiment=pe,
            promoted=True,
            promotion_reason="Causal effect >0.10, CI doesn't cross zero",
            guardian_approved=True,
        )

        assert receipt.promoted
        assert receipt.guardian_approved
        assert receipt.promotion_reason

    def test_receipt_serialization(self):
        """Receipt to_dict."""
        intervention = PolicyIntervention(parameter_name="temperature")
        pe = PolicyExperiment(name="test", intervention=intervention)
        receipt = PolicyChangeReceipt(experiment=pe, promoted=False)

        d = receipt.to_dict()
        assert "receipt_id" in d
        assert "experiment" in d
        assert d["promoted"] is False


class TestPolicyIntegration:
    """Integration: full experiment lifecycle."""

    def test_full_experiment_lifecycle(self):
        """Complete experiment: pre-register → shadow → analyze → promote."""
        # 1. Pre-register experiment
        intervention = PolicyIntervention(
            parameter_name="temperature",
            old_value=0.8,
            new_value=0.5,
            hypothesis="Lower temp → higher confidence",
        )
        pe = PolicyExperiment(
            name="Lower temperature in safety-critical",
            intervention=intervention,
            target_effect=0.10,
            required_sample_size=30,
            stress_scenarios=["healthcare_low_confidence"],
        )

        # 2. Start experiment
        pe.started_at = datetime.utcnow()
        assert pe.is_active

        # 3. Run shadow executions
        se1 = ShadowExecution(
            episode_id="ep_001",
            actual_success=True,
            actual_confidence=0.75,
            shadow_success=True,
            shadow_confidence=0.82,
            validation_regime_identical=True,
        )
        se1.compute_deltas()
        pe.shadow_executions.append(se1)

        se2 = ShadowExecution(
            episode_id="ep_002",
            actual_success=False,
            actual_confidence=0.50,
            shadow_success=True,
            shadow_confidence=0.65,
            validation_regime_identical=True,
        )
        se2.compute_deltas()
        pe.shadow_executions.append(se2)

        # 4. Analyze causal effect
        cs = CausalSummary(
            effect_estimate=0.12,
            ci_lower=0.05,
            ci_upper=0.19,
            method="stratified",
            sample_size=100,
            overlap_check_passed=True,
            validity_concerns=[],
            promotion_recommendation="PROMOTE",
        )
        pe.causal_summary = cs

        # 5. Complete experiment
        pe.ended_at = datetime.utcnow()
        assert pe.is_complete
        assert pe.promotion_eligible

        # 6. Create receipt and promote
        receipt = PolicyChangeReceipt(
            experiment=pe,
            promoted=True,
            promotion_reason="Causal effect meets criteria",
            guardian_approved=True,
        )

        assert receipt.promoted
        assert receipt.experiment.promotion_eligible

    def test_validity_concerns_mandatory(self):
        """Validity concerns field is always present and accessible."""
        cs1 = CausalSummary()
        assert isinstance(cs1.validity_concerns, list)
        assert len(cs1.validity_concerns) == 0

        cs2 = CausalSummary(validity_concerns=["concern1", "concern2"])
        assert len(cs2.validity_concerns) == 2

    def test_insufficient_overlap_detection(self):
        """Detect insufficient overlap in shadow executions."""
        se = ShadowExecution(
            episode_id="ep_001",
            actual_success=True,
            shadow_success=True,
            validation_regime_identical=False,
            validation_mismatch_reason="insufficient overlap: only 5% both policies represented",
        )
        se.compute_deltas()

        assert not se.comparable
