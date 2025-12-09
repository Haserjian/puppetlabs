"""
Causal inference and policy evolution subsystem.

Core modules:
- policy_receipts: PolicyExperiment, PolicyIntervention, ShadowExecution, CausalSummary
- experiment_hooks: ExperimentHook, ExperimentContext, StratificationCovariates
- experiment_registry: ExperimentRegistry, get_experiment_registry
- dataset: generate_causal_dataset, stratified_treatment_effect
"""

from quintet.causal.policy_receipts import (
    PolicyExperiment,
    PolicyIntervention,
    ShadowExecution,
    CausalSummary,
    PolicyChangeReceipt,
    SuccessCriteria,
)
from quintet.causal.experiment_hooks import (
    ExperimentHook,
    ExperimentContext,
    StratificationCovariates,
    get_experiment_hook,
)
from quintet.causal.experiment_registry import (
    ExperimentRegistry,
    get_experiment_registry,
)
from quintet.causal.dataset import (
    generate_causal_dataset,
    stratified_treatment_effect,
)

__all__ = [
    "PolicyExperiment",
    "PolicyIntervention",
    "ShadowExecution",
    "CausalSummary",
    "PolicyChangeReceipt",
    "SuccessCriteria",
    "ExperimentHook",
    "ExperimentContext",
    "StratificationCovariates",
    "get_experiment_hook",
    "ExperimentRegistry",
    "get_experiment_registry",
    "generate_causal_dataset",
    "stratified_treatment_effect",
]
