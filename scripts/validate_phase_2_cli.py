#!/usr/bin/env python3
"""
Phase 2 Validation CLI: Live Loom ↔ Quintet Integration Testing

Validates that Quintet-Loom integration works end-to-end on a running system.

Usage:
    python3 scripts/validate_phase_2_cli.py \\
        --loom-url http://localhost:8000 \\
        --quintet-url http://localhost:9000

Environment variables:
    LOOM_DAEMON_URL: Override --loom-url (default: http://localhost:8000)
    QUINTET_SERVICE_URL: Override --quintet-url (default: http://localhost:9000)
    QUINTET_VALIDATION_RECEIPTS: Receipt storage path (default: .quintet_validation_receipts)

Exit codes:
    0: Phase 2 PASSED (all 3 invariants satisfied)
    1: Phase 2 FAILED (one or more invariants not satisfied)
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
from datetime import datetime
from pathlib import Path

try:
    from quintet.validation.phase2 import run_phase2_validation, summarize_phase2
    from quintet.causal.validation_receipts import create_phase2_receipt
    from quintet.causal.receipt_persistence import ReceiptStore
except ImportError as e:
    print(f"Error: Could not import validation modules: {e}", file=sys.stderr)
    print("Make sure quintet/ is in PYTHONPATH", file=sys.stderr)
    sys.exit(1)


def _print_check(check) -> None:
    """Print a single validation check result."""
    status = "✅" if check.passed else "❌"
    print(f"{status} {check.name}")
    if check.warnings:
        for warning in check.warnings:
            print(f"   ⚠️  {warning}")
    if check.errors:
        for error in check.errors:
            print(f"   ❌ {error}")


def _compute_config_hash(loom_url: str, quintet_url: str) -> dict[str, str]:
    """Compute SHA256 hashes of configuration strings."""
    loom_hash = hashlib.sha256(loom_url.encode()).hexdigest()
    quintet_hash = hashlib.sha256(quintet_url.encode()).hexdigest()
    return {"loom_config_hash": loom_hash, "quintet_config_hash": quintet_hash}


def main(argv: list[str] | None = None) -> int:
    """
    Run Phase 2 validation and mint receipt.

    Args:
        argv: Command-line arguments (for testing)

    Returns:
        0 if Phase 2 PASSED, 1 if FAILED
    """
    parser = argparse.ArgumentParser(
        description="Phase 2 Validation: Live Loom ↔ Quintet Integration"
    )
    parser.add_argument(
        "--loom-url",
        default=os.getenv("LOOM_DAEMON_URL", "http://localhost:8000"),
        help="URL of Loom daemon (default: http://localhost:8000)",
    )
    parser.add_argument(
        "--quintet-url",
        default=os.getenv("QUINTET_SERVICE_URL", "http://localhost:9000"),
        help="URL of Quintet service (default: http://localhost:9000)",
    )
    parser.add_argument(
        "--store-root",
        type=Path,
        default=Path(os.getenv("QUINTET_VALIDATION_RECEIPTS", ".quintet_validation_receipts")),
        help="Root directory for receipt storage",
    )
    parser.add_argument(
        "--loom-profile",
        default="local-test",
        help="Loom configuration profile name (for receipt tracking)",
    )
    parser.add_argument(
        "--timeout",
        type=int,
        default=15,
        help="Timeout for HTTP requests (seconds)",
    )
    parser.add_argument(
        "--policy-change",
        type=json.loads,
        default=None,
        help="Policy change to test as JSON (default: {\"brain_temperature\": 0.8})",
    )

    args = parser.parse_args(argv)

    # Ensure receipt storage directory exists
    args.store_root.mkdir(parents=True, exist_ok=True)

    print("=" * 70)
    print("Phase 2 Validation: Live Loom ↔ Quintet Integration")
    print("=" * 70)
    print()

    # Run validation
    print(f"Testing Loom: {args.loom_url}")
    print(f"Testing Quintet: {args.quintet_url}")
    print()

    try:
        summary = run_phase2_validation(
            loom_daemon_url=args.loom_url,
            quintet_service_url=args.quintet_url,
            test_policy_change=args.policy_change,
        )
    except Exception as e:
        print(f"❌ Validation failed with error: {e}", file=sys.stderr)
        return 1

    # Judge results
    result = summarize_phase2(summary)

    # Print results
    print("Invariant Checks:")
    print()
    for check in summary.checks:
        _print_check(check)
    print()

    # Print summary
    passed = result["passed_checks"]
    total = result["total_checks"]
    print(f"{passed}/{total} checks passed")
    print()

    if result["overall_pass"]:
        print("✅ Phase 2 VALIDATION PASSED")
    else:
        print("❌ Phase 2 VALIDATION FAILED")
        if result["failures"]:
            print()
            print("Failures:")
            for failure in result["failures"]:
                print(f"  • {failure}")

    print()

    # Mint Phase2ValidationReceipt
    try:
        config_hashes = _compute_config_hash(args.loom_url, args.quintet_url)
        receipt = create_phase2_receipt(
            loom_profile=args.loom_profile,
            loom_config_hash=config_hashes["loom_config_hash"],
            quintet_config_hash=config_hashes["quintet_config_hash"],
            checks={c.name: c.passed for c in summary.checks},
            warnings=[w for c in summary.checks for w in c.warnings],
            failures=result["failures"],
            check_live_path=summary.checks[0].passed,
            check_policy_effect=summary.checks[1].passed,
            check_failure_mode=summary.checks[2].passed,
            quintet_calls_observed=summary.checks[0].details.get("calls_observed", 0),
            policy_changes_applied=1 if args.policy_change else 0,
        )

        # Persist receipt
        store = ReceiptStore(storage_path=str(args.store_root / "phase2_receipts.jsonl"))
        saved = store.append_receipt(receipt, verify_chain=False)

        if saved:
            print(f"📜 Validation receipt minted: {receipt.receipt_id}")
            print(f"   Stored in: {args.store_root / 'phase2_receipts.jsonl'}")
        else:
            print(f"⚠️  Receipt created but not saved: {receipt.receipt_id}", file=sys.stderr)

    except Exception as e:
        print(f"⚠️  Could not mint validation receipt: {e}", file=sys.stderr)
        # Continue anyway - validation result is still valid

    print()

    # Return exit code
    return 0 if result["overall_pass"] else 1


if __name__ == "__main__":
    sys.exit(main())
