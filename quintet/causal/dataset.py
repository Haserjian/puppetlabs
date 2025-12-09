"""
Causal Dataset Generation
=========================

Generate causal-ready datasets from episodes and shadow executions
for stratified analysis and causal inference.
"""

from typing import Dict, List, Any, Optional
from pathlib import Path
import json
import logging

logger = logging.getLogger(__name__)


def generate_causal_dataset(
    experiment_id: str,
    registry: "ExperimentRegistry",
    episode_log_path: str = "logs/episodes.jsonl",
) -> Dict[str, List[Dict[str, Any]]]:
    """
    Generate causal-ready dataset from experiment episodes and shadows.

    Returns dataset with columns:
    - episode_id: Unique episode identifier
    - treatment: 0 (control) or 1 (treatment)
    - propensity_score: P(treatment | covariates)
    - stratification_key: Strata for matching
    - outcome_success: Whether episode succeeded (0/1)
    - outcome_confidence: Confidence score (0.0-1.0)
    - outcome_latency_ms: Execution time
    - covariate_*: All stratification covariates
    - shadow_*: Shadow execution outcomes (if available)

    Args:
        experiment_id: ID of experiment to analyze
        registry: ExperimentRegistry with experiment data
        episode_log_path: Path to episodes.jsonl log file

    Returns:
        Dictionary with 'episodes' key containing list of records
    """
    try:
        # Load episodes with experiment metadata
        episodes = _load_episodes_for_experiment(experiment_id, episode_log_path)

        # Load shadow executions
        shadows = registry.get_shadow_executions(experiment_id)

        # Build dataset
        dataset = []
        for episode in episodes:
            record = _episode_to_record(episode)

            # Find corresponding shadow if available
            matching_shadow = _find_matching_shadow(
                episode, shadows, experiment_id
            )
            if matching_shadow:
                record.update(_shadow_to_record(matching_shadow))

            dataset.append(record)

        logger.info(
            f"Generated causal dataset for experiment {experiment_id}: "
            f"{len(dataset)} episodes, {len(shadows)} shadows"
        )

        return {"episodes": dataset}

    except Exception as e:
        logger.error(f"Error generating causal dataset: {e}", exc_info=True)
        raise


def _load_episodes_for_experiment(
    experiment_id: str,
    episode_log_path: str,
) -> List[Dict[str, Any]]:
    """
    Load episodes that are part of a specific experiment.

    Filters episodes.jsonl for those with matching experiment_id in metadata.

    Args:
        experiment_id: ID of experiment
        episode_log_path: Path to episodes.jsonl

    Returns:
        List of episode records
    """
    episodes = []
    log_path = Path(episode_log_path)

    if not log_path.exists():
        logger.warning(f"Episode log not found: {log_path}")
        return episodes

    try:
        with open(log_path) as f:
            for line in f:
                if not line.strip():
                    continue

                try:
                    episode = json.loads(line)

                    # Check if episode belongs to this experiment
                    metadata = episode.get("metadata", {})
                    if metadata.get("experiment_id") == experiment_id:
                        episodes.append(episode)

                except json.JSONDecodeError:
                    logger.debug(f"Failed to parse episode line: {line[:100]}")
                    continue

        logger.info(f"Loaded {len(episodes)} episodes for experiment {experiment_id}")

    except Exception as e:
        logger.error(f"Error loading episodes: {e}")

    return episodes


def _episode_to_record(episode: Dict[str, Any]) -> Dict[str, Any]:
    """Convert episode to causal dataset record."""
    metadata = episode.get("metadata", {})
    result = episode.get("result", {})
    validation = episode.get("validation", {})

    record = {
        "episode_id": episode.get("episode_id", ""),
        "treatment": int(metadata.get("is_treatment", 0)),
        "propensity_score": float(metadata.get("propensity_score", 0.5)),
        "stratification_key": metadata.get("stratification_key", "unknown"),
        "outcome_success": int(result.get("success", False)) if result else 0,
        "outcome_confidence": float(validation.get("confidence", 0.0)) if validation else 0.0,
        "outcome_latency_ms": float(episode.get("duration_ms", 0.0)) if episode else 0.0,
        # Covariates
        "covariate_mode": episode.get("mode", "unknown"),
        "covariate_domain": metadata.get("domain", "unknown"),
        "covariate_problem_type": metadata.get("problem_type", "unknown"),
        "covariate_compute_tier": metadata.get("compute_tier", "standard"),
        "covariate_world_impact": metadata.get("world_impact_category"),
        "covariate_validation_confidence_prior": validation.get("confidence", 0.0) if validation else None,
    }

    return record


def _find_matching_shadow(
    episode: Dict[str, Any],
    shadows: List[Any],
    experiment_id: str,
) -> Optional[Dict[str, Any]]:
    """
    Find shadow execution matching an episode.

    Matches by correlation_id or episode_id.

    Args:
        episode: Episode record
        shadows: List of shadow executions
        experiment_id: Experiment ID (for logging)

    Returns:
        Matching shadow record or None
    """
    episode_id = episode.get("episode_id")
    metadata = episode.get("metadata", {})
    correlation_id = metadata.get("correlation_id")

    # Try correlation_id first (most accurate)
    if correlation_id:
        for shadow in shadows:
            shadow_ep_id = shadow.get("episode_id") if isinstance(shadow, dict) else getattr(shadow, "episode_id", None)
            if shadow_ep_id == correlation_id:
                return shadow

    # Fall back to episode_id
    if episode_id:
        for shadow in shadows:
            shadow_ep_id = shadow.get("episode_id") if isinstance(shadow, dict) else getattr(shadow, "episode_id", None)
            if shadow_ep_id == episode_id:
                return shadow

    return None


def _shadow_to_record(shadow: Any) -> Dict[str, Any]:
    """Convert shadow execution to record fields."""
    # Handle both dict and ShadowExecution object
    if isinstance(shadow, dict):
        shadow_data = shadow
    else:
        shadow_data = shadow.to_dict() if hasattr(shadow, "to_dict") else {}

    actual = shadow_data.get("actual", {})
    shadow_exec = shadow_data.get("shadow", {})
    comparable = shadow_data.get("comparable", False)

    record = {
        "shadow_execution_id": shadow_data.get("execution_id", ""),
        "shadow_comparable": int(comparable),
        "shadow_validation_regime_identical": int(
            shadow_data.get("validation_regime_identical", False)
        ),
        "shadow_outcome_changed": int(shadow_data.get("outcome_changed", False)),
        "shadow_actual_success": int(actual.get("success", False)),
        "shadow_actual_confidence": float(actual.get("confidence", 0.0)),
        "shadow_shadow_success": int(shadow_exec.get("success", False)),
        "shadow_shadow_confidence": float(shadow_exec.get("confidence", 0.0)),
        "shadow_confidence_delta": float(shadow_data.get("confidence_delta", 0.0)),
        "shadow_latency_delta_pct": float(shadow_data.get("latency_delta_pct", 0.0)),
        "shadow_cost_delta_pct": float(shadow_data.get("cost_delta_pct", 0.0)),
    }

    return record


def stratified_treatment_effect(
    dataset: Dict[str, List[Dict[str, Any]]],
    outcome_var: str = "outcome_confidence",
    treatment_var: str = "treatment",
    strata_var: str = "stratification_key",
) -> Dict[str, Any]:
    """
    Compute stratified average treatment effect (SATE).

    Simple stratified analysis: within each strata, compute difference
    in outcomes between treatment and control groups.

    Args:
        dataset: Causal dataset from generate_causal_dataset
        outcome_var: Name of outcome variable
        treatment_var: Name of treatment variable (0/1)
        strata_var: Name of stratification variable

    Returns:
        Dictionary with:
        - ate: Average treatment effect
        - ate_by_strata: Effect within each strata
        - n_treated: Number of treated units
        - n_control: Number of control units
    """
    episodes = dataset.get("episodes", [])

    if not episodes:
        logger.warning("Empty dataset for treatment effect analysis")
        return {"ate": 0.0, "ate_by_strata": {}, "n_treated": 0, "n_control": 0}

    # Group by strata
    strata_groups: Dict[str, Dict[str, List[float]]] = {}

    for record in episodes:
        strata = record.get(strata_var, "unknown")
        treatment = record.get(treatment_var, 0)
        outcome = record.get(outcome_var, 0.0)

        if strata not in strata_groups:
            strata_groups[strata] = {"treated": [], "control": []}

        key = "treated" if treatment else "control"
        strata_groups[strata][key].append(outcome)

    # Compute effects
    effects_by_strata = {}
    total_effect = 0.0
    total_weight = 0.0
    n_treated = 0
    n_control = 0

    for strata, groups in strata_groups.items():
        treated = groups.get("treated", [])
        control = groups.get("control", [])

        if treated and control:
            mean_treated = sum(treated) / len(treated)
            mean_control = sum(control) / len(control)
            effect = mean_treated - mean_control

            # Weight by strata size
            weight = len(treated) + len(control)
            total_effect += effect * weight
            total_weight += weight

            effects_by_strata[strata] = {
                "effect": effect,
                "n_treated": len(treated),
                "n_control": len(control),
                "mean_treated": mean_treated,
                "mean_control": mean_control,
            }

            n_treated += len(treated)
            n_control += len(control)

    # Compute ATE
    ate = total_effect / total_weight if total_weight > 0 else 0.0

    return {
        "ate": ate,
        "ate_by_strata": effects_by_strata,
        "n_treated": n_treated,
        "n_control": n_control,
        "n_strata": len(strata_groups),
    }
