#!/usr/bin/env python3
"""
Phase 1 Validation CLI

Thin wrapper around quintet.validation.phase1 invariants.
Loads fixture, runs checks, prints status, mints a validation receipt, returns exit code.

Usage:
    python3 scripts/validate_phase_1_cli.py [fixture_path]

Output:
    - Console report with check results
    - Phase1ValidationReceipt minted to .quintet_validation_receipts/
"""

from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

# Add parent directory to path so we can import quintet
sys.path.insert(0, str(Path(__file__).parent.parent))

from quintet.validation.phase1 import run_phase1_validation, summarize_phase1
from quintet.validation.types import ValidationCheckResult, ValidationSummary
from quintet.causal.validation_receipts import create_phase1_receipt
from quintet.causal.receipt_persistence import ReceiptStore, compute_receipt_hash


DEFAULT_FIXTURE = Path("tests/fixtures/loom_export_sample.json")


def _print_check(check: ValidationCheckResult) -> None:
    """Pretty-print a single check result."""
    if check.passed:
        icon = "✅"
    elif check.errors:
        icon = "❌"
    else:
        icon = "⚠️"

    print(f"{icon} {check.name}")

    if check.warnings:
        for w in check.warnings:
            print(f"   ⚠️  {w}")
    if check.errors:
        for e in check.errors:
            print(f"   ❌ {e}")


def main(argv: list[str] | None = None) -> int:
    """Run Phase 1 validation, mint a receipt, and return exit code."""
    print("=" * 70)
    print("PHASE 1 VALIDATION: Real Data Test")
    print("=" * 70)

    argv = argv or sys.argv[1:]

    if argv:
        fixture_path = Path(argv[0])
    else:
        fixture_path = DEFAULT_FIXTURE

    if not fixture_path.exists():
        print(f"❌ Fixture not found: {fixture_path}")
        return 1

    print(f"\n📖 Loading episodes from {fixture_path}...")
    try:
        fixture_data = fixture_path.read_text()
        data = json.loads(fixture_data)
    except Exception as e:
        print(f"❌ Failed to load fixture: {e}")
        return 1

    # Compute fixture hash for receipt
    fixture_hash = hashlib.sha256(fixture_data.encode()).hexdigest()

    # Adjust if your fixture wraps episodes under a key
    episodes = data.get("episodes", data)

    if not isinstance(episodes, list):
        print(f"❌ Fixture does not contain 'episodes' list")
        return 1

    print(f"   ✓ Loaded {len(episodes)} episodes")
    print(f"   ✓ Fixture hash: {fixture_hash[:16]}...")

    # Run library-level validation
    summary: ValidationSummary = run_phase1_validation(episodes)
    result = summarize_phase1(summary)

    # Print each check
    print("\n" + "=" * 70)
    print("CHECKS")
    print("=" * 70)
    for check in summary.checks:
        _print_check(check)

    # Print summary
    print("\n" + "=" * 70)
    print("PHASE 1 RESULTS")
    print("=" * 70)
    print(f"\n📊 {result['passed_checks']}/{result['total_checks']} checks passed")
    if result["warnings"]:
        print(f"   {result['warnings']} warnings")
    if result["failures"]:
        print(f"   {len(result['failures'])} failure(s): {', '.join(result['failures'])}")

    print(f"\n{result['message']}")

    # Mint a Phase1ValidationReceipt
    checks_dict = {check.name: check.passed for check in summary.checks}
    warnings_list = []
    for check in summary.checks:
        warnings_list.extend(check.warnings)
    failures_list = result["failures"]

    receipt = create_phase1_receipt(
        fixture_path=str(fixture_path),
        fixture_hash=fixture_hash,
        fixture_episode_count=len(episodes),
        checks=checks_dict,
        warnings=warnings_list,
        failures=failures_list,
        tool_version="quintet-phase1-v1.1",
    )

    # Persist the receipt
    try:
        store_root = Path(".quintet_validation_receipts")
        store_root.mkdir(parents=True, exist_ok=True)
        store = ReceiptStore(storage_path=str(store_root / "phase1_receipts.jsonl"))
        saved = store.append_receipt(receipt, verify_chain=False)
        print(f"\n📜 Validation receipt minted: {receipt.receipt_id}")
        print(f"   Stored in: {store_root / 'phase1_receipts.jsonl'}")
    except Exception as e:
        print(f"\n⚠️  Warning: Could not persist validation receipt: {e}")
        # Don't fail the validation just because we couldn't store the receipt
        pass

    return 0 if result["overall_pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
