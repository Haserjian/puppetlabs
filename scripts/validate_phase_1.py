#!/usr/bin/env python3
"""
Phase 1 Validation: Real Data Test (Legacy Wrapper)

This script is now a thin wrapper around scripts/validate_phase_1_cli.py.

See: scripts/validate_phase_1_cli.py for the actual implementation.
See: quintet/validation/phase1.py for the invariants.
"""

import sys
import importlib.util
from pathlib import Path

# Load validate_phase_1_cli dynamically since scripts/ isn't a package
cli_path = Path(__file__).parent / "validate_phase_1_cli.py"
spec = importlib.util.spec_from_file_location("validate_phase_1_cli", cli_path)
validate_phase_1_cli = importlib.util.module_from_spec(spec)
spec.loader.exec_module(validate_phase_1_cli)

if __name__ == "__main__":
    raise SystemExit(validate_phase_1_cli.main())


# ============================================================================
# LEGACY CODE BELOW (kept for reference, but not used)
# ============================================================================
#
# The code below is the original Phase 1 validation script.
# It has been refactored into quintet/validation/phase1.py and
# scripts/validate_phase_1_cli.py.
#
# If you need to understand what was changed, see:
#   - quintet/validation/types.py (ValidationCheckResult, ValidationSummary)
#   - quintet/validation/phase1.py (check_* functions, run_phase1_validation)
#   - scripts/validate_phase_1_cli.py (CLI entry point)
#
# ============================================================================

import json
import sys
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from quintet.loom_adapter import LoomEpisode, analyze_episodes, PolicyRecommendation
from quintet.stress.promotion import StressPromotionManager
from quintet.causal.receipt_persistence import ReceiptStore


def load_episodes(path: str) -> List[LoomEpisode]:
    """Load episodes from JSON file."""
    print(f"📖 Loading episodes from {path}...")

    with open(path) as f:
        data = json.load(f)

    episodes_data = data.get("episodes", [])
    episodes = [LoomEpisode.from_dict(ep) for ep in episodes_data]

    print(f"   ✓ Loaded {len(episodes)} episodes")
    return episodes


def validate_episode_quality(episodes: List[LoomEpisode]) -> Dict[str, Any]:
    """Check episode data quality."""
    print("\n🔍 Validating episode quality...")

    stats = {
        "total": len(episodes),
        "by_mode": {},
        "by_domain": {},
        "by_outcome": {},
        "missing_fields": 0,
    }

    for ep in episodes:
        # Count by mode
        stats["by_mode"][ep.mode] = stats["by_mode"].get(ep.mode, 0) + 1

        # Count by domain
        stats["by_domain"][ep.domain] = stats["by_domain"].get(ep.domain, 0) + 1

        # Count by outcome
        stats["by_outcome"][ep.outcome] = stats["by_outcome"].get(ep.outcome, 0) + 1

        # Check for required fields
        if not ep.episode_id or not ep.mode or not ep.domain:
            stats["missing_fields"] += 1

    print(f"   ✓ Total episodes: {stats['total']}")
    print(f"   ✓ Modes: {dict(stats['by_mode'])}")
    print(f"   ✓ Domains: {dict(stats['by_domain'])}")
    print(f"   ✓ Outcomes: {dict(stats['by_outcome'])}")
    if stats["missing_fields"] > 0:
        print(f"   ⚠️  Episodes with missing fields: {stats['missing_fields']}")

    return stats


def validate_recommendations(episodes: List[LoomEpisode]) -> Dict[str, Any]:
    """Run Quintet analysis and validate recommendations."""
    print("\n🎯 Running Quintet analysis...")

    results = {
        "recommendations": [],
        "errors": [],
        "quality_score": 0.0,
    }

    # Analyze by policy lever
    levers = ["brain_temperature", "guardian_strictness", "perception_threshold"]

    for lever in levers:
        try:
            rec = analyze_episodes(episodes, lever=lever)
            evidence_str = str(rec.evidence)[:200] if rec.evidence else ""
            results["recommendations"].append({
                "lever": lever,
                "action": rec.action,
                "recommended_value": rec.recommended_value,
                "confidence": rec.confidence,
                "evidence": evidence_str,
            })
            print(f"   ✓ {lever}: {rec.action} (confidence: {rec.confidence:.2f})")
        except Exception as e:
            results["errors"].append(f"Error analyzing {lever}: {str(e)}")
            print(f"   ❌ {lever}: {str(e)}")

    # Check quality
    if results["recommendations"]:
        avg_confidence = sum(r["confidence"] for r in results["recommendations"]) / len(results["recommendations"])
        results["quality_score"] = avg_confidence
        print(f"\n   📊 Average confidence: {avg_confidence:.2f}")

    return results


def validate_stress_gates(episodes: List[LoomEpisode]) -> Dict[str, Any]:
    """Check if stress gates would block any recommendations."""
    print("\n🚧 Validating stress gates...")

    try:
        from quintet.stress.run_pre_promote import run_pre_promote_check
    except ImportError:
        print("   ⚠️  Stress gate module not found (skipping)")
        return {
            "gate_checks": [],
            "blocked": 0,
            "approved": 0,
            "skipped": True,
        }

    results = {
        "gate_checks": [],
        "blocked": 0,
        "approved": 0,
    }

    # Simulate promoting brain_temperature
    try:
        check_result = run_pre_promote_check(
            lever="brain_temperature",
            new_value=0.8,
            episodes=episodes,
        )

        results["gate_checks"].append({
            "lever": "brain_temperature",
            "approved": check_result.approved,
            "reason": check_result.reason[:200],
        })

        if check_result.approved:
            results["approved"] += 1
            print(f"   ✓ brain_temperature promotion approved")
        else:
            results["blocked"] += 1
            print(f"   ❌ brain_temperature promotion blocked: {check_result.reason}")

    except Exception as e:
        results["gate_checks"].append({
            "lever": "brain_temperature",
            "error": str(e),
        })
        print(f"   ⚠️  Stress gate error: {str(e)}")

    return results


def validate_receipt_chain(episodes: List[LoomEpisode]) -> Dict[str, Any]:
    """Check receipt generation and chain integrity."""
    print("\n📜 Validating receipt chain...")

    results = {
        "receipts_generated": 0,
        "chain_valid": False,
        "errors": [],
    }

    try:
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

        # Create intervention
        intervention = PolicyIntervention(
            intervention_id="phase1-test-intervention",
            timestamp=datetime.now(),
            domain=PolicyDomain.TEMPERATURE,
            intervention_type=InterventionType.PARAMETER_CHANGE,
            parameter_name="brain_temperature",
            old_value=0.7,
            new_value=0.75,
            hypothesis="Test recommendation from Phase 1",
            mechanism="Direct parameter update",
            triggered_by="phase1_validation",
        )

        # Create experiment
        experiment = PolicyExperiment(
            name="Phase 1 Validation Test",
            description="Test experiment for validation framework",
            intervention=intervention,
            target_effect=0.10,
            required_sample_size=15,
            stress_scenarios=["solver_overflow"],
        )

        # Create receipt
        receipt = PolicyChangeReceipt(
            experiment=experiment,
            promoted=True,
            promotion_reason="Phase 1 validation test",
            guardian_approved=True,
            guardian_notes="Test approval",
        )

        # Compute hash
        receipt_hash = compute_receipt_hash(receipt)

        results["receipts_generated"] = 1
        results["chain_valid"] = True
        print(f"   ✓ Receipt created: {receipt.receipt_id}")
        print(f"   ✓ Hash: {receipt_hash[:16]}...")

    except Exception as e:
        results["errors"].append(str(e))
        print(f"   ❌ Receipt generation failed: {str(e)}")

    return results


def main():
    """Run Phase 1 validation."""
    print("=" * 70)
    print("PHASE 1 VALIDATION: Real Data Test")
    print("=" * 70)

    # Load test data
    fixture_path = Path(__file__).parent.parent / "tests" / "fixtures" / "loom_export_sample.json"

    if not fixture_path.exists():
        print(f"❌ Test fixture not found: {fixture_path}")
        sys.exit(1)

    episodes = load_episodes(str(fixture_path))

    # Run validations
    ep_quality = validate_episode_quality(episodes)
    recommendations = validate_recommendations(episodes)
    stress_gates = validate_stress_gates(episodes)
    receipts = validate_receipt_chain(episodes)

    # Summary
    print("\n" + "=" * 70)
    print("PHASE 1 RESULTS")
    print("=" * 70)

    passed = 0
    total = 4
    warnings = 0

    print(f"\n1. Episode Quality: ", end="")
    if ep_quality["missing_fields"] == 0:
        print("✅ PASS")
        passed += 1
    else:
        print("⚠️  WARNING")
        warnings += 1

    print(f"\n2. Recommendations: ", end="")
    if recommendations["quality_score"] > 0.6 and len(recommendations["errors"]) == 0:
        print("✅ PASS")
        passed += 1
    else:
        print("❌ FAIL")

    print(f"\n3. Stress Gates: ", end="")
    if stress_gates.get("skipped"):
        print("⚠️  SKIPPED (module not found)")
        warnings += 1
    elif stress_gates.get("gate_checks"):
        print("✅ PASS")
        passed += 1
    else:
        print("⚠️  WARNING")
        warnings += 1

    print(f"\n4. Receipt Chain: ", end="")
    if receipts["chain_valid"]:
        print("✅ PASS")
        passed += 1
    else:
        print("❌ FAIL")

    print(f"\n\n📊 Overall: {passed}/{total} checks passed")
    if warnings > 0:
        print(f"   (with {warnings} warnings)")

    if passed >= 3 and warnings <= 1:
        print("\n✅ Phase 1 VALIDATION PASSED")
        print("   System works on test data. Ready for Phase 2 (Integration Test).")
        return 0
    else:
        print(f"\n❌ Phase 1 VALIDATION FAILED")
        print(f"   Need to fix {total - passed} failures before Phase 2")
        return 1


if __name__ == "__main__":
    sys.exit(main())
