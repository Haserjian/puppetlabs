"""
Quintet Validation: structured validation framework for integration testing.

Exposes:
  - ValidationCheckResult: atomic check result
  - ValidationSummary: aggregated summary
  - Phase 1: Test data validation (fixture-based)
  - Phase 2: Live system integration (Loom ↔ Quintet)
"""

from quintet.validation.types import ValidationCheckResult, ValidationSummary
from quintet.validation.phase1 import (
    run_phase1_validation,
    summarize_phase1,
    check_episode_quality,
    check_recommendations,
    check_stress_gates,
    check_receipt_chain,
)
from quintet.validation.phase2 import (
    run_phase2_validation,
    summarize_phase2,
    check_live_path,
    check_policy_effect,
    check_failure_mode,
)

__all__ = [
    # Types
    "ValidationCheckResult",
    "ValidationSummary",
    # Phase 1
    "run_phase1_validation",
    "summarize_phase1",
    "check_episode_quality",
    "check_recommendations",
    "check_stress_gates",
    "check_receipt_chain",
    # Phase 2
    "run_phase2_validation",
    "summarize_phase2",
    "check_live_path",
    "check_policy_effect",
    "check_failure_mode",
]
