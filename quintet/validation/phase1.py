"""
Phase 1 Validation: Real Data Test

Invariants:
  1. Episode quality: exported episodes are structurally sound
  2. Recommendations: Quintet analysis runs without errors and produces coherent output
  3. Stress gates: pre-promotion safety checks are available (CLI or API)
  4. Receipt chain: policy change receipts can be constructed, hashed, and persisted

All checks return ValidationCheckResult; the CLI interprets them.
"""

from __future__ import annotations

import json
from dataclasses import asdict
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Tuple

from quintet.validation.types import ValidationCheckResult, ValidationSummary
from quintet.causal.policy_receipts import (
    PolicyChangeReceipt,
    PolicyExperiment,
    PolicyIntervention,
    InterventionType,
    PolicyDomain,
)
from quintet.causal.receipt_persistence import (
    ReceiptStore,
    compute_receipt_hash,
)
from quintet.loom_adapter import LoomEpisode, analyze_episodes


# ---------- Helpers ----------


def _require_keys(obj: Dict[str, Any], keys: List[str]) -> List[str]:
    """Return list of missing keys in obj."""
    return [k for k in keys if k not in obj]


def _dict_to_loom_episode(ep_dict: Dict[str, Any]) -> LoomEpisode:
    """Convert raw episode dict to LoomEpisode."""
    return LoomEpisode.from_dict(ep_dict)


# ---------- Check 1: Episode Quality ----------


def check_episode_quality(episodes: List[Dict[str, Any]]) -> ValidationCheckResult:
    """
    Invariant: Episode export is structurally sane.

    Minimal invariants for Phase 1:
      - At least 1 episode
      - Each episode can be parsed as LoomEpisode
      - No missing required fields
    """
    name = "episode_quality"
    warnings: List[str] = []
    errors: List[str] = []

    if not episodes:
        errors.append("No episodes found in export.")
        return ValidationCheckResult(
            name=name,
            passed=False,
            warnings=warnings,
            errors=errors,
            details={"episode_count": 0},
        )

    missing_fields_total = 0
    parse_errors: List[Tuple[str, str]] = []

    for ep_dict in episodes:
        ep_id = ep_dict.get("episode_id", "<unknown>")
        try:
            episode = _dict_to_loom_episode(ep_dict)
        except Exception as e:
            parse_errors.append((ep_id, str(e)))
            continue

        # Check for basic fields after parsing
        required = ["mode", "outcome"]
        missing = _require_keys(ep_dict, required)
        missing_fields_total += len(missing)

    if parse_errors:
        errors.append(f"{len(parse_errors)} episodes failed to parse.")
        warnings.append("See details.parse_errors for which episodes couldn't be loaded.")

    if missing_fields_total > 0:
        errors.append(f"{missing_fields_total} required fields missing across episodes.")

    return ValidationCheckResult(
        name=name,
        passed=len(errors) == 0,
        warnings=warnings,
        errors=errors,
        details={
            "episode_count": len(episodes),
            "missing_fields": missing_fields_total,
            "parse_errors": parse_errors,
        },
    )


# ---------- Check 2: Recommendations ----------


def check_recommendations(episodes: List[Dict[str, Any]]) -> ValidationCheckResult:
    """
    Invariant: Recommendations produced by Quintet on these episodes are coherent.

    Phase 1 invariant:
      - We can run the analysis pipeline without throwing
      - Average confidence >= 0.6
      - No internal errors reported by analyzer
    """
    name = "recommendations"
    warnings: List[str] = []
    errors: List[str] = []
    details: Dict[str, Any] = {
        "levers_tested": [],
        "quality_scores": [],
    }

    if not episodes:
        errors.append("Cannot check recommendations without episodes.")
        return ValidationCheckResult(
            name=name,
            passed=False,
            warnings=warnings,
            errors=errors,
            details=details,
        )

    # Convert raw dicts to LoomEpisode objects
    try:
        loom_episodes = [_dict_to_loom_episode(ep) for ep in episodes]
    except Exception as e:
        errors.append(f"Failed to convert episodes to LoomEpisode: {e}")
        return ValidationCheckResult(
            name=name,
            passed=False,
            warnings=warnings,
            errors=errors,
            details=details,
        )

    # Analyze by policy lever
    levers = ["brain_temperature", "guardian_strictness", "perception_threshold"]
    quality_scores = []
    rec_errors = []

    for lever in levers:
        try:
            rec = analyze_episodes(loom_episodes, lever=lever)
            score = rec.confidence
            quality_scores.append(score)
            details["levers_tested"].append(
                {
                    "lever": lever,
                    "action": rec.action,
                    "confidence": score,
                }
            )
        except Exception as e:
            rec_errors.append(f"Error analyzing {lever}: {str(e)}")
            errors.append(f"Error analyzing {lever}: {str(e)}")

    if quality_scores:
        avg_confidence = sum(quality_scores) / len(quality_scores)
        details["quality_scores"] = quality_scores
        details["avg_confidence"] = avg_confidence

        if avg_confidence < 0.6:
            errors.append(
                f"Average confidence below threshold: {avg_confidence:.2f} < 0.6"
            )
    else:
        errors.append("No valid recommendations were generated.")

    return ValidationCheckResult(
        name=name,
        passed=len(errors) == 0,
        warnings=warnings,
        errors=errors,
        details=details,
    )


# ---------- Check 3: Stress Gates ----------


def check_stress_gates() -> ValidationCheckResult:
    """
    Invariant: A pre-promotion stress gate exists and can be invoked.

    For Phase 1.1, we treat "CLI-only, not yet importable" as explicit state.
    The CLI logic then decides whether to block Phase 1 based on this.
    """
    name = "stress_gates"
    warnings: List[str] = []
    errors: List[str] = []
    details: Dict[str, Any] = {}

    try:
        # Check if CLI script exists
        script_path = (
            Path(__file__).resolve().parents[1] / "stress" / "run_pre_promote.py"
        )
        if not script_path.exists():
            errors.append("Stress gate CLI script not found.")
            details["mode"] = "missing"
            return ValidationCheckResult(
                name=name,
                passed=False,
                warnings=warnings,
                errors=errors,
                details=details,
            )

        # CLI exists; explicitly mark "available but only via CLI"
        warnings.append("Stress gates available only via CLI; no importable API yet.")
        details["mode"] = "cli_only"
        details["cli_path"] = str(script_path)

        # For Phase 1, this is not a hard failure (passed=False but no errors)
        # Higher phases can tighten the requirement
        return ValidationCheckResult(
            name=name,
            passed=False,  # invariant not fully satisfied (no programmatic API)
            warnings=warnings,
            errors=[],  # but no hard errors
            details=details,
        )

    except Exception as e:
        errors.append(f"Stress gate check failed unexpectedly: {e}")
        return ValidationCheckResult(
            name=name,
            passed=False,
            warnings=warnings,
            errors=errors,
            details=details,
        )


# ---------- Check 4: Receipt Chain / Persistence ----------


def check_receipt_chain(store_root: Path | None = None) -> ValidationCheckResult:
    """
    Invariant: Policy change receipts can be constructed, hashed, and persisted.

    Phase 1.1 advances from smoke test to actual round-trip:
      - Construct PolicyIntervention + PolicyExperiment + PolicyChangeReceipt
      - Compute a stable hash via compute_receipt_hash
      - Persist via ReceiptStore
      - Reload and verify hash stability
    """
    name = "receipt_chain"
    warnings: List[str] = []
    errors: List[str] = []
    details: Dict[str, Any] = {}

    try:
        # 1) Build intervention / experiment / receipt
        intervention = PolicyIntervention(
            intervention_id="phase1-test-intervention",
            timestamp=datetime.now(),
            domain=PolicyDomain.TEMPERATURE,
            intervention_type=InterventionType.PARAMETER_CHANGE,
            parameter_name="brain_temperature",
            old_value=0.7,
            new_value=0.75,
            hypothesis="Test recommendation from Phase 1 validation",
            mechanism="Direct parameter update",
            triggered_by="phase1_validation",
        )

        experiment = PolicyExperiment(
            name="Phase 1 Validation Test",
            description="Test experiment for validation framework",
            intervention=intervention,
            target_effect=0.10,
            required_sample_size=15,
            stress_scenarios=["solver_overflow"],
        )

        receipt = PolicyChangeReceipt(
            experiment=experiment,
            promoted=True,
            promotion_reason="Phase 1 validation test",
            guardian_approved=True,
            guardian_notes="Test approval",
        )

        # 2) Compute hash before persistence
        pre_hash = compute_receipt_hash(receipt)
        details["pre_hash_prefix"] = pre_hash[:16]
        details["receipt_id"] = getattr(receipt, "receipt_id", None)

        # 3) Persist via ReceiptStore
        if store_root is None:
            store_root = Path(".quintet_receipts_phase1_validation")
        store_root.mkdir(parents=True, exist_ok=True)

        store = ReceiptStore(storage_path=str(store_root / "receipts.jsonl"))
        receipt_with_hash = store.append_receipt(receipt, verify_chain=True)
        details["saved_receipt_id"] = receipt.receipt_id

        # 4) Reload and recompute hash
        all_receipts = store.read_all_receipts(verify_chain=False)
        if not all_receipts:
            errors.append("Receipt was not persisted to store.")
        else:
            # Find our receipt in the list
            loaded_receipt = None
            for rwh in all_receipts:
                if rwh.receipt.receipt_id == receipt.receipt_id:
                    loaded_receipt = rwh
                    break

            if loaded_receipt is None:
                errors.append(
                    f"Receipt {receipt.receipt_id} not found after reload."
                )
            else:
                post_hash = compute_receipt_hash(loaded_receipt.receipt)
                details["post_hash_prefix"] = post_hash[:16]

                if pre_hash != post_hash:
                    errors.append(
                        f"Receipt hash not stable: pre={pre_hash} vs post={post_hash}"
                    )

    except Exception as e:
        errors.append(f"Receipt chain/persistence check failed: {e}")
        import traceback

        details["error_traceback"] = traceback.format_exc()

    return ValidationCheckResult(
        name=name,
        passed=len(errors) == 0,
        warnings=warnings,
        errors=errors,
        details=details,
    )


# ---------- Runner & Summary ----------


def run_phase1_validation(
    episodes: List[Dict[str, Any]],
    store_root: Path | None = None,
) -> ValidationSummary:
    """
    Run all Phase 1 validation checks and return a summary.

    Args:
        episodes: List of episode dicts (from JSON export)
        store_root: Optional path to root for ReceiptStore; defaults to .quintet_receipts_phase1_validation

    Returns:
        ValidationSummary with all check results
    """
    checks: List[ValidationCheckResult] = []

    checks.append(check_episode_quality(episodes))
    checks.append(check_recommendations(episodes))
    checks.append(check_stress_gates())
    checks.append(check_receipt_chain(store_root=store_root))

    return ValidationSummary(checks=checks)


def summarize_phase1(summary: ValidationSummary) -> Dict[str, Any]:
    """
    Compute human-friendly pass/warn/fail judgment.

    Phase 1 passes if:
      - At least 3 checks passed
      - No checks have failures (only warnings allowed for some)

    Returns dict with keys:
        passed_checks: count of passed checks
        warnings: count of warnings
        failures: list of failed check names
        overall_pass: bool whether Phase 1 passed
        message: human-readable summary
    """
    passed = summary.passed_checks
    total = summary.total_checks
    warnings = summary.warnings_count
    failures = summary.failures

    # Phase 1 passes if we have 3+ checks passing and no hard failures
    overall_pass = (passed >= 3) and (len(failures) == 0)

    if overall_pass:
        message = (
            f"✅ Phase 1 VALIDATION PASSED\n"
            f"   System works on test data. Ready for Phase 2 (Integration Test)."
        )
    elif passed >= 3:
        message = (
            f"⚠️  Phase 1 VALIDATION INCOMPLETE (warnings only)\n"
            f"   {len(failures)} check(s) have warnings but no hard failures.\n"
            f"   Review the warnings before Phase 2."
        )
    else:
        message = (
            f"❌ Phase 1 VALIDATION FAILED\n"
            f"   {len(failures)} check(s) have hard failures.\n"
            f"   Fix these before Phase 2."
        )

    return {
        "passed_checks": passed,
        "total_checks": total,
        "warnings": warnings,
        "failures": failures,
        "overall_pass": overall_pass,
        "message": message,
    }
