"""
Causal Experiment Hooks for Safe Policy Learning
=================================================

Injects policy interventions into execution flow and captures shadow outcomes
for causal inference. Enables safe policy evolution through randomized experiments
and observational analysis.

Key responsibilities:
- Decide if episode should be in experiment (randomization or observational)
- Apply policy intervention if treatment group
- Capture shadow execution if control group
- Link episode to experiment via correlation_id
- Compute propensity scores for observational analysis
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple, Any
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor
import uuid
import logging
import random

from quintet.causal.policy_receipts import PolicyIntervention, ShadowExecution

logger = logging.getLogger(__name__)


@dataclass
class StratificationCovariates:
    """Covariates used for stratification and propensity score computation."""

    mode: str
    domain: Optional[str] = None
    problem_type: Optional[str] = None
    compute_tier: str = "standard"
    world_impact_category: Optional[str] = None
    validation_confidence_prior: Optional[float] = None

    def to_strata_key(self) -> str:
        """Compute stratification key for matching treatment/control."""
        parts = [
            self.mode,
            self.domain or "unknown",
            self.problem_type or "unknown",
            self.compute_tier,
        ]
        return ":".join(parts)


@dataclass
class ExperimentContext:
    """Context for an ongoing experiment during episode execution."""

    experiment_id: str
    correlation_id: str  # Links episode → shadow → experiment
    intervention: PolicyIntervention
    is_treatment: bool  # True if this episode gets intervention
    propensity_score: float  # P(treatment | covariates)
    stratification_key: str  # For matching treatment/control
    covariates: StratificationCovariates = field(default_factory=lambda: StratificationCovariates(mode="unknown"))


class ExperimentHook:
    """
    Manages policy experiments during execution.

    Wraps execution to apply interventions, capture shadows, and track
    causal metadata linking episodes to experiments.
    """

    def __init__(self, experiment_registry: "ExperimentRegistry"):
        """
        Initialize experiment hook.

        Args:
            experiment_registry: Registry for active experiments and shadow results
        """
        self.registry = experiment_registry
        self.thread_pool = ThreadPoolExecutor(max_workers=4)
        self._logger = logger

    def check_and_assign(
        self,
        query: str,
        intent: Any,
        problem: Any,
        plan: Any,
    ) -> Optional[ExperimentContext]:
        """
        Check if episode should be in experiment and assign treatment/control.

        Args:
            query: Original user query
            intent: Detected intent (e.g., MathIntent, BuildIntent)
            problem: Problem structure
            plan: Solution plan

        Returns:
            ExperimentContext if episode is part of active experiment, None otherwise
        """
        # Check for active experiments
        active_experiments = self.registry.get_active_experiments()
        if not active_experiments:
            return None

        # Extract stratification covariates
        covariates = self._extract_covariates(intent, problem, plan)

        # Select experiment (simple: pick first active)
        experiment = active_experiments[0]

        # Assign treatment (randomize 50/50)
        is_treatment = self._assign_treatment(experiment, covariates)
        propensity = self._compute_propensity_score(covariates, experiment)

        # Create experiment context
        ctx = ExperimentContext(
            experiment_id=experiment.experiment_id,
            correlation_id=str(uuid.uuid4()),
            intervention=experiment.intervention,
            is_treatment=is_treatment,
            propensity_score=propensity,
            stratification_key=covariates.to_strata_key(),
            covariates=covariates,
        )

        self._logger.info(
            f"Assigned episode to experiment {experiment.experiment_id}: "
            f"treatment={is_treatment}, propensity={propensity:.2f}, "
            f"strata={ctx.stratification_key}"
        )

        return ctx

    def apply_intervention(
        self,
        resource_limits: Dict[str, Any],
        intervention: PolicyIntervention,
    ) -> Dict[str, Any]:
        """
        Apply policy intervention to resource limits or other parameters.

        Args:
            resource_limits: Current resource limits
            intervention: PolicyIntervention to apply

        Returns:
            Modified resource limits
        """
        modified = resource_limits.copy() if resource_limits else {}

        # Apply intervention based on parameter name
        if intervention.parameter_name == "temperature_cap":
            # Temperature interventions affect sampling behavior
            # Store in metadata for executor to apply
            if "__interventions" not in modified:
                modified["__interventions"] = []
            modified["__interventions"].append(
                {
                    "parameter": intervention.parameter_name,
                    "old_value": intervention.old_value,
                    "new_value": intervention.new_value,
                }
            )

        elif intervention.parameter_name == "model_slot":
            # Model slot interventions affect which model to use
            modified["model_slot"] = intervention.new_value

        elif intervention.parameter_name == "validation_regime":
            # Validation regime interventions affect validation depth
            modified["validation_regime"] = intervention.new_value

        self._logger.debug(
            f"Applied intervention: {intervention.parameter_name} "
            f"{intervention.old_value} → {intervention.new_value}"
        )

        return modified

    def capture_shadow_async(
        self,
        experiment_ctx: ExperimentContext,
        actual_result: Dict[str, Any],
        problem: Any,
        plan: Any,
        validation: Any,
    ) -> None:
        """
        Asynchronously capture shadow execution with opposite policy.

        Submitted to thread pool - returns immediately.

        Args:
            experiment_ctx: Experiment context for this episode
            actual_result: Result from actual execution
            problem: Problem being solved
            plan: Solution plan
            validation: Validation result from actual execution
        """
        self.thread_pool.submit(
            self._execute_shadow_internal,
            experiment_ctx,
            actual_result,
            problem,
            plan,
            validation,
        )

    def _execute_shadow_internal(
        self,
        ctx: ExperimentContext,
        actual_result: Dict[str, Any],
        problem: Any,
        plan: Any,
        actual_validation: Any,
    ) -> None:
        """
        Internal method to execute shadow and log to registry.

        Runs in thread pool.
        """
        try:
            # Build shadow execution
            shadow = self._build_shadow_execution(
                ctx=ctx,
                actual_result=actual_result,
                problem=problem,
                plan=plan,
                actual_validation=actual_validation,
            )

            # Record to registry
            self.registry.record_shadow_execution(ctx.experiment_id, shadow)

            self._logger.info(
                f"Shadow execution completed: episode {shadow.episode_id}, "
                f"comparable={shadow.comparable}"
            )

        except Exception as e:
            self._logger.error(f"Error executing shadow: {e}", exc_info=True)

    def _extract_covariates(
        self,
        intent: Any,
        problem: Any,
        plan: Any,
    ) -> StratificationCovariates:
        """Extract stratification covariates from execution context."""
        mode = getattr(intent, "mode", "unknown")
        domain = getattr(intent, "domain", None)
        problem_type = getattr(intent, "problem_type", None)
        compute_tier = getattr(intent, "compute_tier", "standard")
        world_impact_category = None

        # If problem has world_impact assessment
        if hasattr(problem, "world_impact"):
            world_impact_category = getattr(problem.world_impact, "category", None)

        return StratificationCovariates(
            mode=str(mode),
            domain=str(domain) if domain else None,
            problem_type=str(problem_type) if problem_type else None,
            compute_tier=str(compute_tier),
            world_impact_category=world_impact_category,
        )

    def _assign_treatment(
        self,
        experiment: Any,
        covariates: StratificationCovariates,
    ) -> bool:
        """
        Assign treatment status (randomization).

        For now: simple 50/50 randomization.
        Future: propensity-score based for observational studies.
        """
        # Check if experiment specifies randomization
        randomized = experiment.details.get("randomized", True) if hasattr(experiment, "details") else True

        if randomized:
            return random.random() < 0.5

        # Observational: use propensity score
        propensity = self._compute_propensity_score(covariates, experiment)
        return random.random() < propensity

    def _compute_propensity_score(
        self,
        covariates: StratificationCovariates,
        experiment: Any,
    ) -> float:
        """
        Compute P(treatment | covariates).

        For randomized experiments: 0.5
        For observational: model-based (simple baseline model for now)
        """
        # For randomized experiments, propensity is 0.5
        if experiment.details.get("randomized", True) if hasattr(experiment, "details") else True:
            return 0.5

        # Observational: simple logistic model
        propensity = 0.5

        # Adjust based on covariates
        if covariates.compute_tier == "deep_search":
            propensity *= 1.2  # More resources → more likely intervention

        if covariates.world_impact_category:
            propensity *= 0.7  # High impact → less likely (safety first)

        # Clip to valid range
        return min(max(propensity, 0.01), 0.99)

    def _build_shadow_execution(
        self,
        ctx: ExperimentContext,
        actual_result: Dict[str, Any],
        problem: Any,
        plan: Any,
        actual_validation: Any,
    ) -> ShadowExecution:
        """Build ShadowExecution object from actual and shadow results."""
        # Extract metrics from actual result
        actual_success = actual_result.get("success", False) if actual_result else False
        actual_confidence = actual_result.get("confidence", 0.0) if actual_result else 0.0
        actual_latency_ms = actual_result.get("duration_ms", 0.0) if actual_result else 0.0
        actual_cost = actual_result.get("cost", 0.0) if actual_result else 0.0

        # For now, shadow result would be captured by orchestrator
        # Here we create placeholder ShadowExecution
        shadow_success = actual_success  # Placeholder
        shadow_confidence = actual_confidence  # Placeholder
        shadow_latency_ms = actual_latency_ms  # Placeholder
        shadow_cost = actual_cost  # Placeholder

        # Validation regime consistency (placeholder - actual would compare checks)
        validation_regime_identical = True
        validation_mismatch_reason = ""

        shadow = ShadowExecution(
            episode_id=ctx.correlation_id,
            actual_success=actual_success,
            actual_confidence=actual_confidence,
            actual_latency_ms=actual_latency_ms,
            actual_cost=actual_cost,
            shadow_success=shadow_success,
            shadow_confidence=shadow_confidence,
            shadow_latency_ms=shadow_latency_ms,
            shadow_cost=shadow_cost,
            validation_regime_identical=validation_regime_identical,
            validation_mismatch_reason=validation_mismatch_reason,
        )

        # Compute deltas
        shadow.compute_deltas()

        return shadow

    def shutdown(self) -> None:
        """Shutdown thread pool."""
        self.thread_pool.shutdown(wait=True)


# Global singleton registry (will be initialized)
_experiment_registry: Optional["ExperimentRegistry"] = None


def get_experiment_hook(registry: Optional["ExperimentRegistry"] = None) -> ExperimentHook:
    """
    Get or create global experiment hook.

    Args:
        registry: Optional registry to use. If None, uses global registry.

    Returns:
        ExperimentHook instance
    """
    if registry is None:
        from quintet.causal.experiment_registry import get_experiment_registry

        registry = get_experiment_registry()

    return ExperimentHook(registry)
