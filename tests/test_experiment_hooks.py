"""
Tests for Causal Experiment Hooks: treatment assignment, stratification, registry, dataset generation.
"""

import pytest
import json
from pathlib import Path
from datetime import datetime
from unittest.mock import Mock, MagicMock

from quintet.causal.experiment_hooks import (
    ExperimentHook,
    ExperimentContext,
    StratificationCovariates,
    get_experiment_hook,
)
from quintet.causal.experiment_registry import (
    ExperimentRegistry,
    get_experiment_registry,
    reset_registry,
)
from quintet.causal.policy_receipts import (
    PolicyExperiment,
    PolicyIntervention,
    ShadowExecution,
    PolicyDomain,
    InterventionType,
    SuccessCriteria,
)
from quintet.causal.dataset import (
    generate_causal_dataset,
    stratified_treatment_effect,
)


class TestStratificationCovariates:
    """Test stratification covariate extraction and key generation."""

    def test_stratification_key_generation(self):
        """Generate stratification key from covariates."""
        covariates = StratificationCovariates(
            mode="math",
            domain="algebra",
            problem_type="solve",
            compute_tier="standard",
            world_impact_category="low",
        )

        key = covariates.to_strata_key()
        assert key == "math:algebra:solve:standard"

    def test_stratification_key_with_none_values(self):
        """Handle None values in stratification key."""
        covariates = StratificationCovariates(
            mode="math",
            domain=None,
            problem_type=None,
            compute_tier="light",
        )

        key = covariates.to_strata_key()
        assert key == "math:unknown:unknown:light"

    def test_stratification_covariates_defaults(self):
        """Stratification covariates have sensible defaults."""
        covariates = StratificationCovariates(mode="build")
        assert covariates.mode == "build"
        assert covariates.compute_tier == "standard"
        assert covariates.domain is None
        assert covariates.world_impact_category is None


class TestExperimentHook:
    """Test experiment hook core functionality."""

    @pytest.fixture
    def registry(self, tmp_path):
        """Create temporary registry."""
        return ExperimentRegistry(str(tmp_path / "experiments"))

    @pytest.fixture
    def hook(self, registry):
        """Create experiment hook."""
        return ExperimentHook(registry)

    @pytest.fixture
    def active_experiment(self):
        """Create a simple active experiment."""
        intervention = PolicyIntervention(
            parameter_name="temperature",
            old_value=0.8,
            new_value=0.5,
            hypothesis="Lower temperature reduces harm",
        )

        experiment = PolicyExperiment(
            name="Test Temperature Experiment",
            intervention=intervention,
            target_effect=0.10,
        )

        experiment.started_at = datetime.utcnow()
        # Don't set ended_at so is_active is True

        return experiment

    def test_check_and_assign_no_active_experiments(self, hook):
        """Return None when no active experiments."""
        ctx = hook.check_and_assign(
            query="test",
            intent=Mock(mode="math"),
            problem=Mock(),
            plan=Mock(),
        )

        assert ctx is None

    def test_check_and_assign_creates_context(self, hook, registry, active_experiment):
        """Create experiment context when experiment is active."""
        registry.register_experiment(active_experiment)

        ctx = hook.check_and_assign(
            query="test",
            intent=Mock(mode="math", domain="algebra", problem_type="solve", compute_tier="standard"),
            problem=Mock(world_impact=None),
            plan=Mock(),
        )

        assert ctx is not None
        assert ctx.experiment_id == active_experiment.experiment_id
        assert ctx.correlation_id is not None
        assert ctx.is_treatment in [True, False]
        assert 0.01 <= ctx.propensity_score <= 0.99

    def test_treatment_assignment_randomization(self, hook, registry, active_experiment):
        """Treatment assignment randomizes 50/50."""
        registry.register_experiment(active_experiment)

        covariates = StratificationCovariates(mode="math", compute_tier="standard")

        # Run 100 assignments
        assignments = []
        for _ in range(100):
            is_treatment = hook._assign_treatment(active_experiment, covariates)
            assignments.append(is_treatment)

        treatment_rate = sum(assignments) / len(assignments)
        # Should be close to 50%, within reasonable bounds (30-70%)
        assert 0.3 <= treatment_rate <= 0.7

    def test_propensity_score_computation(self, hook, active_experiment):
        """Compute propensity scores for covariates."""
        # Randomized experiment: propensity = 0.5
        covariates = StratificationCovariates(mode="math")
        propensity = hook._compute_propensity_score(covariates, active_experiment)
        assert propensity == 0.5

    def test_extract_covariates(self, hook):
        """Extract stratification covariates from intent and problem."""
        intent = Mock(
            mode="math",
            domain="calculus",
            problem_type="integrate",
            compute_tier="deep_search",
        )
        problem = Mock(world_impact=Mock(category="decision_support"))
        plan = Mock()

        covariates = hook._extract_covariates(intent, problem, plan)

        assert covariates.mode == "math"
        assert covariates.domain == "calculus"
        assert covariates.problem_type == "integrate"
        assert covariates.compute_tier == "deep_search"
        assert covariates.world_impact_category == "decision_support"

    def test_apply_intervention_temperature(self, hook):
        """Apply temperature intervention to resource limits."""
        limits = {"max_tokens": 10000}

        intervention = PolicyIntervention(
            parameter_name="temperature_cap",
            old_value=0.8,
            new_value=0.5,
        )

        modified = hook.apply_intervention(limits, intervention)

        assert "__interventions" in modified
        assert len(modified["__interventions"]) > 0
        assert modified["__interventions"][0]["parameter"] == "temperature_cap"

    def test_build_shadow_execution(self, hook):
        """Build shadow execution object."""
        ctx = ExperimentContext(
            experiment_id="exp-001",
            correlation_id="corr-001",
            intervention=PolicyIntervention(parameter_name="temperature"),
            is_treatment=True,
            propensity_score=0.5,
            stratification_key="math:algebra:solve:standard",
        )

        actual_result = {
            "success": True,
            "confidence": 0.85,
            "duration_ms": 100.0,
            "cost": 0.05,
        }

        shadow = hook._build_shadow_execution(
            ctx=ctx,
            actual_result=actual_result,
            problem=Mock(),
            plan=Mock(),
            actual_validation=Mock(),
        )

        assert shadow is not None
        assert shadow.episode_id == "corr-001"
        assert shadow.actual_success is True
        assert shadow.actual_confidence == 0.85
        assert shadow.validation_regime_identical is True


class TestExperimentRegistry:
    """Test experiment registry thread safety and persistence."""

    @pytest.fixture
    def registry(self, tmp_path):
        """Create temporary registry."""
        return ExperimentRegistry(str(tmp_path / "experiments"))

    def test_register_experiment(self, registry):
        """Register an experiment."""
        experiment = PolicyExperiment(name="Test Experiment")
        experiment.started_at = datetime.utcnow()

        registry.register_experiment(experiment)

        assert registry.get_experiment(experiment.experiment_id) is not None
        assert experiment in registry.get_active_experiments()

    def test_get_active_experiments(self, registry):
        """Get only active experiments."""
        # Create active experiment
        active = PolicyExperiment(name="Active")
        active.started_at = datetime.utcnow()

        # Create inactive experiment
        inactive = PolicyExperiment(name="Inactive")

        registry.register_experiment(active)
        registry.register_experiment(inactive)

        active_list = registry.get_active_experiments()

        assert len(active_list) == 1
        assert active_list[0].experiment_id == active.experiment_id

    def test_record_shadow_execution(self, registry):
        """Record shadow execution to registry."""
        experiment = PolicyExperiment(name="Test")
        experiment.started_at = datetime.utcnow()
        registry.register_experiment(experiment)

        shadow = ShadowExecution(
            episode_id="ep-001",
            actual_success=True,
            shadow_success=True,
        )

        registry.record_shadow_execution(experiment.experiment_id, shadow)

        shadows = registry.get_shadow_executions(experiment.experiment_id)
        assert len(shadows) == 1
        assert shadows[0].episode_id == "ep-001"

    def test_get_experiment_data(self, registry):
        """Get complete experiment data."""
        experiment = PolicyExperiment(name="Test")
        experiment.started_at = datetime.utcnow()
        registry.register_experiment(experiment)

        shadow = ShadowExecution(episode_id="ep-001")
        registry.record_shadow_execution(experiment.experiment_id, shadow)

        data = registry.get_experiment_data(experiment.experiment_id)

        assert data["experiment"] is not None
        assert len(data["shadows"]) == 1
        assert data["metadata"] is not None

    def test_list_experiments(self, registry):
        """List all experiment IDs."""
        exp1 = PolicyExperiment(name="Exp 1")
        exp1.started_at = datetime.utcnow()
        exp2 = PolicyExperiment(name="Exp 2")
        exp2.started_at = datetime.utcnow()

        registry.register_experiment(exp1)
        registry.register_experiment(exp2)

        exp_ids = registry.list_experiments()

        assert len(exp_ids) == 2
        assert exp1.experiment_id in exp_ids
        assert exp2.experiment_id in exp_ids

    def test_persist_experiment_to_disk(self, registry, tmp_path):
        """Persist experiment metadata to disk."""
        experiment = PolicyExperiment(name="Test")
        experiment.started_at = datetime.utcnow()
        registry.register_experiment(experiment)

        # Check files exist
        exp_dir = tmp_path / "experiments" / experiment.experiment_id
        assert exp_dir.exists()
        assert (exp_dir / "metadata.json").exists()

    def test_persist_shadow_to_disk(self, registry, tmp_path):
        """Persist shadow execution to append-only JSONL."""
        experiment = PolicyExperiment(name="Test")
        experiment.started_at = datetime.utcnow()
        registry.register_experiment(experiment)

        shadow = ShadowExecution(episode_id="ep-001")
        registry.record_shadow_execution(experiment.experiment_id, shadow)

        # Check file exists and contains shadow
        exp_dir = tmp_path / "experiments" / experiment.experiment_id
        shadows_file = exp_dir / "shadows.jsonl"

        assert shadows_file.exists()

        with open(shadows_file) as f:
            lines = f.readlines()
            assert len(lines) == 1

            data = json.loads(lines[0])
            assert data["episode_id"] == "ep-001"


class TestGlobalRegistry:
    """Test global singleton registry."""

    def teardown_method(self):
        """Reset registry after each test."""
        reset_registry()

    def test_get_experiment_registry_singleton(self):
        """Get global registry singleton."""
        reg1 = get_experiment_registry()
        reg2 = get_experiment_registry()

        assert reg1 is reg2

    def test_get_experiment_hook(self):
        """Get experiment hook with global registry."""
        hook = get_experiment_hook()

        assert hook is not None
        assert isinstance(hook, ExperimentHook)


class TestCausalDatasetGeneration:
    """Test causal dataset generation from episodes and shadows."""

    @pytest.fixture
    def registry(self, tmp_path):
        """Create registry."""
        return ExperimentRegistry(str(tmp_path / "experiments"))

    @pytest.fixture
    def episodes_file(self, tmp_path):
        """Create episodes JSONL file."""
        episodes_path = tmp_path / "episodes.jsonl"

        episodes = [
            {
                "episode_id": "ep-001",
                "mode": "math",
                "metadata": {
                    "experiment_id": "exp-001",
                    "is_treatment": 1,
                    "propensity_score": 0.5,
                    "stratification_key": "math:algebra:solve:standard",
                    "domain": "algebra",
                    "problem_type": "solve",
                    "compute_tier": "standard",
                },
                "result": {"success": True},
                "validation": {"confidence": 0.85},
                "duration_ms": 100.0,
            },
            {
                "episode_id": "ep-002",
                "mode": "math",
                "metadata": {
                    "experiment_id": "exp-001",
                    "is_treatment": 0,
                    "propensity_score": 0.5,
                    "stratification_key": "math:algebra:solve:standard",
                    "domain": "algebra",
                    "problem_type": "solve",
                    "compute_tier": "standard",
                },
                "result": {"success": True},
                "validation": {"confidence": 0.75},
                "duration_ms": 110.0,
            },
        ]

        with open(episodes_path, "w") as f:
            for ep in episodes:
                json.dump(ep, f)
                f.write("\n")

        return str(episodes_path)

    def test_generate_causal_dataset(self, registry, episodes_file):
        """Generate causal dataset from episodes."""
        dataset = generate_causal_dataset(
            experiment_id="exp-001",
            registry=registry,
            episode_log_path=episodes_file,
        )

        assert "episodes" in dataset
        episodes = dataset["episodes"]
        assert len(episodes) == 2

        # Check record structure
        record = episodes[0]
        assert "episode_id" in record
        assert "treatment" in record
        assert "propensity_score" in record
        assert "stratification_key" in record
        assert "outcome_success" in record
        assert "outcome_confidence" in record
        assert "covariate_mode" in record

    def test_stratified_treatment_effect(self, registry, episodes_file):
        """Compute stratified average treatment effect."""
        dataset = generate_causal_dataset(
            experiment_id="exp-001",
            registry=registry,
            episode_log_path=episodes_file,
        )

        effect = stratified_treatment_effect(dataset)

        assert "ate" in effect
        assert "ate_by_strata" in effect
        assert "n_treated" in effect
        assert "n_control" in effect

        assert effect["n_treated"] == 1
        assert effect["n_control"] == 1


class TestExperimentHookIntegration:
    """Integration tests for full experiment lifecycle."""

    @pytest.fixture
    def registry(self, tmp_path):
        """Create registry."""
        return ExperimentRegistry(str(tmp_path / "experiments"))

    @pytest.fixture
    def hook(self, registry):
        """Create hook."""
        return ExperimentHook(registry)

    def test_full_experiment_lifecycle(self, hook, registry):
        """Test complete experiment from registration to data retrieval."""
        # 1. Create and register experiment
        intervention = PolicyIntervention(
            parameter_name="temperature",
            old_value=0.8,
            new_value=0.5,
        )

        experiment = PolicyExperiment(
            name="Temperature Test",
            intervention=intervention,
            target_effect=0.10,
        )

        experiment.started_at = datetime.utcnow()

        registry.register_experiment(experiment)

        # 2. Simulate 10 episodes
        for i in range(10):
            ctx = hook.check_and_assign(
                query=f"test {i}",
                intent=Mock(mode="math", domain="algebra", compute_tier="standard", problem_type="solve"),
                problem=Mock(world_impact=None),
                plan=Mock(),
            )

            assert ctx is not None
            assert ctx.experiment_id == experiment.experiment_id

            # Record shadow
            shadow = ShadowExecution(
                episode_id=ctx.correlation_id,
                actual_success=True,
                actual_confidence=0.8 + 0.01 * i,
            )

            registry.record_shadow_execution(experiment.experiment_id, shadow)

        # 3. Retrieve data
        data = registry.get_experiment_data(experiment.experiment_id)

        assert data["experiment"] is not None
        assert len(data["shadows"]) == 10
        assert data["metadata"]["shadow_executions_count"] == 10

    def test_treatment_assignment_balance(self, hook, registry):
        """Verify treatment assignment creates balanced groups."""
        experiment = PolicyExperiment(name="Balance Test")
        experiment.started_at = datetime.utcnow()
        registry.register_experiment(experiment)

        treatments = []
        for i in range(100):
            ctx = hook.check_and_assign(
                query=f"test {i}",
                intent=Mock(mode="math", domain="algebra", compute_tier="standard", problem_type="solve"),
                problem=Mock(world_impact=None),
                plan=Mock(),
            )

            treatments.append(ctx.is_treatment)

        treatment_rate = sum(treatments) / len(treatments)

        # Should be approximately 50/50 (allow 35-65% range for randomness)
        assert 0.35 <= treatment_rate <= 0.65
