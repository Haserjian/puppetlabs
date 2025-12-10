#!/usr/bin/env python3
"""
Invariant Checker for Claude Code Quality Gates

This script runs as a hook to verify project invariants haven't been violated.
Exit codes:
  0 = All checks passed
  1 = Warnings (non-blocking)
  2 = Critical failures (blocks the operation)

Usage:
  python scripts/check_invariants.py [--strict]
"""

import argparse
import os
import re
import subprocess
import sys
from pathlib import Path
from typing import NamedTuple


class CheckResult(NamedTuple):
    passed: bool
    message: str
    critical: bool = False


def check_no_secrets_in_code() -> CheckResult:
    """Check for hardcoded secrets in source files."""
    secret_patterns = [
        r'(?i)(api[_-]?key|apikey)\s*[=:]\s*["\'][^"\']{10,}["\']',
        r'(?i)(secret|password|passwd|pwd)\s*[=:]\s*["\'][^"\']{8,}["\']',
        r'(?i)(token)\s*[=:]\s*["\'][^"\']{20,}["\']',
        r'sk-[a-zA-Z0-9]{20,}',  # OpenAI keys
        r'ghp_[a-zA-Z0-9]{36}',  # GitHub tokens
        r'AKIA[0-9A-Z]{16}',  # AWS access keys
    ]

    violations = []
    source_extensions = {'.py', '.js', '.ts', '.tsx', '.jsx', '.json', '.yaml', '.yml'}

    for root, _, files in os.walk('.'):
        # Skip common non-source directories
        if any(skip in root for skip in ['.git', 'node_modules', '__pycache__', '.venv', 'venv']):
            continue

        for file in files:
            if Path(file).suffix not in source_extensions:
                continue

            filepath = Path(root) / file
            try:
                content = filepath.read_text(encoding='utf-8', errors='ignore')
                for pattern in secret_patterns:
                    matches = re.findall(pattern, content)
                    if matches:
                        violations.append(f"{filepath}: Potential secret found")
                        break
            except Exception:
                pass

    if violations:
        return CheckResult(
            passed=False,
            message=f"Potential secrets detected:\n" + "\n".join(violations[:5]),
            critical=True
        )
    return CheckResult(passed=True, message="No hardcoded secrets found")


def check_type_hints() -> CheckResult:
    """Check that Python functions have type hints."""
    missing_hints = []

    for root, _, files in os.walk('.'):
        if any(skip in root for skip in ['.git', 'node_modules', '__pycache__', '.venv', 'venv', 'tests']):
            continue

        for file in files:
            if not file.endswith('.py'):
                continue

            filepath = Path(root) / file
            try:
                content = filepath.read_text(encoding='utf-8')
                # Find function definitions without return type hints
                # This is a simple check - not perfect but catches obvious cases
                untyped = re.findall(
                    r'^def\s+(\w+)\s*\([^)]*\)\s*:',
                    content,
                    re.MULTILINE
                )
                typed = re.findall(
                    r'^def\s+(\w+)\s*\([^)]*\)\s*->',
                    content,
                    re.MULTILINE
                )

                for func in untyped:
                    if func not in typed and not func.startswith('_'):
                        missing_hints.append(f"{filepath}: {func}()")
            except Exception:
                pass

    if missing_hints:
        return CheckResult(
            passed=False,
            message=f"Functions missing type hints:\n" + "\n".join(missing_hints[:10]),
            critical=False  # Warning, not blocking
        )
    return CheckResult(passed=True, message="Type hints look good")


def check_tests_exist() -> CheckResult:
    """Check that test files exist for source modules."""
    tests_dir = Path('tests')
    if not tests_dir.exists():
        return CheckResult(
            passed=False,
            message="No tests/ directory found",
            critical=False
        )

    test_files = list(tests_dir.glob('**/test_*.py')) + list(tests_dir.glob('**/*_test.py'))
    if not test_files:
        return CheckResult(
            passed=False,
            message="No test files found in tests/",
            critical=False
        )

    return CheckResult(passed=True, message=f"Found {len(test_files)} test file(s)")


def check_no_debug_code() -> CheckResult:
    """Check for leftover debug code."""
    debug_patterns = [
        r'breakpoint\(\)',
        r'import\s+pdb',
        r'pdb\.set_trace\(\)',
        r'console\.log\(',  # In Python files (copy-paste error)
        r'print\(["\']DEBUG',
        r'# TODO.*REMOVE',
        r'# HACK',
        r'debugger;',
    ]

    violations = []
    source_extensions = {'.py', '.js', '.ts', '.tsx', '.jsx'}

    for root, _, files in os.walk('.'):
        if any(skip in root for skip in ['.git', 'node_modules', '__pycache__', '.venv', 'venv']):
            continue

        for file in files:
            if Path(file).suffix not in source_extensions:
                continue

            filepath = Path(root) / file
            try:
                content = filepath.read_text(encoding='utf-8', errors='ignore')
                for pattern in debug_patterns:
                    if re.search(pattern, content):
                        violations.append(f"{filepath}: Contains debug code ({pattern})")
                        break
            except Exception:
                pass

    if violations:
        return CheckResult(
            passed=False,
            message=f"Debug code found:\n" + "\n".join(violations[:5]),
            critical=False
        )
    return CheckResult(passed=True, message="No debug code found")


def check_large_files() -> CheckResult:
    """Check for unusually large files that might be mistakes."""
    max_size_mb = 5
    large_files = []

    for root, _, files in os.walk('.'):
        if any(skip in root for skip in ['.git', 'node_modules', '__pycache__', '.venv', 'venv']):
            continue

        for file in files:
            filepath = Path(root) / file
            try:
                size_mb = filepath.stat().st_size / (1024 * 1024)
                if size_mb > max_size_mb:
                    large_files.append(f"{filepath}: {size_mb:.1f}MB")
            except Exception:
                pass

    if large_files:
        return CheckResult(
            passed=False,
            message=f"Large files detected (>{max_size_mb}MB):\n" + "\n".join(large_files),
            critical=False
        )
    return CheckResult(passed=True, message="No unusually large files")


def run_all_checks(strict: bool = False) -> int:
    """Run all invariant checks and return exit code."""
    checks = [
        ("Secrets Check", check_no_secrets_in_code),
        ("Type Hints", check_type_hints),
        ("Tests Exist", check_tests_exist),
        ("Debug Code", check_no_debug_code),
        ("Large Files", check_large_files),
    ]

    print("=" * 60)
    print("INVARIANT CHECKER")
    print("=" * 60)

    has_critical = False
    has_warning = False

    for name, check_fn in checks:
        result = check_fn()

        if result.passed:
            status = "✓ PASS"
        elif result.critical:
            status = "✗ FAIL (CRITICAL)"
            has_critical = True
        else:
            status = "⚠ WARN"
            has_warning = True

        print(f"\n{status}: {name}")
        if not result.passed:
            print(f"  {result.message}")

    print("\n" + "=" * 60)

    if has_critical:
        print("RESULT: BLOCKED - Critical issues must be fixed")
        return 2
    elif has_warning and strict:
        print("RESULT: BLOCKED (strict mode) - Warnings treated as errors")
        return 2
    elif has_warning:
        print("RESULT: PASSED with warnings")
        return 0
    else:
        print("RESULT: ALL CHECKS PASSED")
        return 0


def main():
    parser = argparse.ArgumentParser(description="Check project invariants")
    parser.add_argument(
        "--strict",
        action="store_true",
        help="Treat warnings as errors"
    )
    args = parser.parse_args()

    sys.exit(run_all_checks(strict=args.strict))


if __name__ == "__main__":
    main()
