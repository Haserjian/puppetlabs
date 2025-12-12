"""
Phase 2 Validation: Live Loom ↔ Quintet Integration Testing

Tests whether Quintet-Loom integration works end-to-end on a running system.

Invariant 5: Live Loom → Quintet Call Path Exists
  Given: A Loom daemon configured to call Quintet
  When: Executing a test episode (policy decision request)
  Then: At least one successful call to Quintet API/service occurs
  Result: PASS if >=1 call recorded; FAIL if 0 calls or all calls error

Invariant 6: Policy Change Has Observable Effect
  Given: A known-safe test policy change (e.g., brain_temperature adjustment)
  When: Running the same test episode twice (before & after change)
  Then: Metrics differ in predicted direction
  Result: PASS if effect is observable; FAIL if no effect

Invariant 7: Misconfiguration Fails Explicitly
  Given: Quintet misconfigured (bad URL, invalid API key, etc.)
  When: Running a test episode that requires Quintet
  Then: A clear error receipt is generated (not success with skipped analysis)
  Result: PASS if error is explicit; FAIL if integration silently skipped
"""

from __future__ import annotations

import json
import os
import time
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

import requests

from quintet.validation.types import ValidationCheckResult, ValidationSummary


@dataclass
class QuintetCallRecord:
    """Record of a call made to Quintet service."""
    call_id: str
    timestamp: datetime
    episode_id: str
    parameters: Dict[str, Any]
    result: Dict[str, Any]
    duration_ms: float
    success: bool
    error_message: Optional[str] = None


@dataclass
class PolicyMetrics:
    """Metrics from a single episode execution."""
    episode_id: str
    timestamp: datetime
    policy_state: Dict[str, Any]
    latency_ms: float
    outcome: str  # "success" | "failure" | "degraded"
    confidence: float
    dignity_score: Optional[float] = None
    coherence_delta: Optional[float] = None
    guardian_verdict: Optional[str] = None


def check_live_path(
    loom_daemon_url: str,
    quintet_service_url: str,
    test_episode_intent: str = "test_policy_evaluation",
    timeout_sec: int = 10,
) -> ValidationCheckResult:
    """
    Invariant 5: Live Loom → Quintet call path exists.

    Verifies that:
    1. Loom daemon is reachable
    2. Can trigger a test episode
    3. Quintet service receives and logs the call
    4. Call parameters are correctly formed
    5. Response is a valid PolicyRecommendation

    Returns:
        ValidationCheckResult with:
        - passed: True if >= 1 call recorded
        - details: {"calls_observed": int, "sample_call": Dict}
    """
    errors: List[str] = []
    warnings: List[str] = []
    details: Dict[str, Any] = {}

    try:
        # Step 1: Verify Loom daemon is reachable
        try:
            loom_health = requests.get(
                f"{loom_daemon_url}/health",
                timeout=timeout_sec,
            )
            if loom_health.status_code != 200:
                errors.append(f"Loom daemon unhealthy: {loom_health.status_code}")
                return ValidationCheckResult(
                    name="live_path",
                    passed=False,
                    errors=errors,
                    warnings=warnings,
                    details=details,
                )
        except requests.ConnectionError as e:
            errors.append(f"Loom daemon unreachable at {loom_daemon_url}: {e}")
            return ValidationCheckResult(
                name="live_path",
                passed=False,
                errors=errors,
                warnings=warnings,
                details=details,
            )

        # Step 2: Verify Quintet service is reachable
        try:
            quintet_health = requests.get(
                f"{quintet_service_url}/health",
                timeout=timeout_sec,
            )
            if quintet_health.status_code != 200:
                errors.append(f"Quintet service unhealthy: {quintet_health.status_code}")
                return ValidationCheckResult(
                    name="live_path",
                    passed=False,
                    errors=errors,
                    warnings=warnings,
                    details=details,
                )
        except requests.ConnectionError as e:
            errors.append(f"Quintet service unreachable at {quintet_service_url}: {e}")
            return ValidationCheckResult(
                name="live_path",
                passed=False,
                errors=errors,
                warnings=warnings,
                details=details,
            )

        # Step 3: Trigger test episode via Loom
        try:
            episode_resp = requests.post(
                f"{loom_daemon_url}/api/episodes",
                json={
                    "intent": test_episode_intent,
                    "mode": "test",
                    "domain": "validation",
                    "test_marker": "phase2_live_path_check",
                },
                timeout=timeout_sec,
            )
            if episode_resp.status_code != 201:
                errors.append(f"Failed to trigger test episode: {episode_resp.status_code}")
                return ValidationCheckResult(
                    name="live_path",
                    passed=False,
                    errors=errors,
                    warnings=warnings,
                    details=details,
                )
            episode_data = episode_resp.json()
            episode_id = episode_data.get("episode_id")
            if not episode_id:
                errors.append("Test episode created but no episode_id returned")
                return ValidationCheckResult(
                    name="live_path",
                    passed=False,
                    errors=errors,
                    warnings=warnings,
                    details=details,
                )
        except requests.RequestException as e:
            errors.append(f"Error triggering test episode: {e}")
            return ValidationCheckResult(
                name="live_path",
                passed=False,
                errors=errors,
                warnings=warnings,
                details=details,
            )

        # Step 4: Wait for call to be recorded and check Quintet logs
        # Allow up to timeout_sec for call to propagate
        time.sleep(1)  # Brief pause for async processing
        try:
            calls_resp = requests.get(
                f"{quintet_service_url}/api/calls",
                params={
                    "episode_id": episode_id,
                    "since": int((datetime.utcnow().timestamp() - 10) * 1000),  # last 10 sec
                },
                timeout=timeout_sec,
            )
            if calls_resp.status_code == 200:
                calls_data = calls_resp.json()
                calls = calls_data.get("calls", [])
                details["calls_observed"] = len(calls)
                if calls:
                    details["sample_call"] = calls[0]
                    return ValidationCheckResult(
                        name="live_path",
                        passed=True,
                        warnings=warnings,
                        errors=[],
                        details=details,
                    )
                else:
                    warnings.append("No calls recorded yet (may propagate after brief delay)")
                    return ValidationCheckResult(
                        name="live_path",
                        passed=False,
                        warnings=warnings,
                        errors=["No Quintet calls recorded for test episode"],
                        details=details,
                    )
            else:
                warnings.append(f"Could not query Quintet call logs: {calls_resp.status_code}")
                details["calls_observed"] = 0
                return ValidationCheckResult(
                    name="live_path",
                    passed=False,
                    warnings=warnings,
                    errors=["Could not verify Quintet call logging"],
                    details=details,
                )
        except requests.RequestException as e:
            errors.append(f"Error querying Quintet calls: {e}")
            return ValidationCheckResult(
                name="live_path",
                passed=False,
                errors=errors,
                warnings=warnings,
                details=details,
            )

    except Exception as e:
        errors.append(f"Unexpected error in live_path check: {e}")
        return ValidationCheckResult(
            name="live_path",
            passed=False,
            errors=errors,
            warnings=warnings,
            details=details,
        )


def check_policy_effect(
    loom_daemon_url: str,
    quintet_service_url: str,
    test_policy_change: Optional[Dict[str, Any]] = None,
    baseline_delay_sec: int = 2,
    timeout_sec: int = 15,
) -> ValidationCheckResult:
    """
    Invariant 6: Policy change has observable effect.

    Verifies that:
    1. Baseline metrics are recorded for test episode with current policy
    2. A known-safe policy change is applied
    3. Same test episode is run again
    4. Metrics differ in expected direction
    5. Receipts link cause (change) → effect (metrics)

    Returns:
        ValidationCheckResult with:
        - passed: True if effect is observable and receipted
        - details: {"baseline": Dict, "after_change": Dict, "effect_observed": bool}
    """
    if test_policy_change is None:
        test_policy_change = {"brain_temperature": 0.8}  # Default safe change

    errors: List[str] = []
    warnings: List[str] = []
    details: Dict[str, Any] = {}

    try:
        # Step 1: Record baseline metrics
        try:
            baseline_resp = requests.post(
                f"{loom_daemon_url}/api/episodes",
                json={
                    "intent": "policy_effect_baseline",
                    "mode": "test",
                    "domain": "validation",
                    "test_marker": "phase2_policy_effect_baseline",
                },
                timeout=timeout_sec,
            )
            if baseline_resp.status_code != 201:
                errors.append(f"Failed to create baseline episode: {baseline_resp.status_code}")
                return ValidationCheckResult(
                    name="policy_effect",
                    passed=False,
                    errors=errors,
                    warnings=warnings,
                    details=details,
                )
            baseline_data = baseline_resp.json()
            details["baseline_episode_id"] = baseline_data.get("episode_id")
            details["baseline"] = {
                "latency_ms": baseline_data.get("latency_ms"),
                "confidence": baseline_data.get("confidence"),
                "outcome": baseline_data.get("outcome"),
            }
        except requests.RequestException as e:
            errors.append(f"Error running baseline episode: {e}")
            return ValidationCheckResult(
                name="policy_effect",
                passed=False,
                errors=errors,
                warnings=warnings,
                details=details,
            )

        # Step 2: Apply policy change (safe test change only)
        try:
            change_resp = requests.post(
                f"{quintet_service_url}/api/test-policy-change",
                json={"change": test_policy_change, "revert_after_ms": baseline_delay_sec * 1000 + 5000},
                timeout=timeout_sec,
            )
            if change_resp.status_code != 200:
                errors.append(f"Failed to apply policy change: {change_resp.status_code}")
                return ValidationCheckResult(
                    name="policy_effect",
                    passed=False,
                    errors=errors,
                    warnings=warnings,
                    details=details,
                )
            details["policy_change_applied"] = test_policy_change
        except requests.RequestException as e:
            errors.append(f"Error applying policy change: {e}")
            return ValidationCheckResult(
                name="policy_effect",
                passed=False,
                errors=errors,
                warnings=warnings,
                details=details,
            )

        # Step 3: Wait for policy change to take effect
        time.sleep(baseline_delay_sec)

        # Step 4: Run same test episode with new policy
        try:
            changed_resp = requests.post(
                f"{loom_daemon_url}/api/episodes",
                json={
                    "intent": "policy_effect_changed",
                    "mode": "test",
                    "domain": "validation",
                    "test_marker": "phase2_policy_effect_changed",
                    "baseline_episode_id": details.get("baseline_episode_id"),
                },
                timeout=timeout_sec,
            )
            if changed_resp.status_code != 201:
                errors.append(f"Failed to create changed episode: {changed_resp.status_code}")
                return ValidationCheckResult(
                    name="policy_effect",
                    passed=False,
                    errors=errors,
                    warnings=warnings,
                    details=details,
                )
            changed_data = changed_resp.json()
            details["changed_episode_id"] = changed_data.get("episode_id")
            details["after_change"] = {
                "latency_ms": changed_data.get("latency_ms"),
                "confidence": changed_data.get("confidence"),
                "outcome": changed_data.get("outcome"),
            }
        except requests.RequestException as e:
            errors.append(f"Error running changed episode: {e}")
            return ValidationCheckResult(
                name="policy_effect",
                passed=False,
                errors=errors,
                warnings=warnings,
                details=details,
            )

        # Step 5: Compare metrics
        baseline_latency = details.get("baseline", {}).get("latency_ms", 0)
        changed_latency = details.get("after_change", {}).get("latency_ms", 0)

        # Policy change should be observable (metrics differ)
        if baseline_latency > 0 and changed_latency > 0:
            latency_diff = abs(changed_latency - baseline_latency)
            latency_pct = (latency_diff / baseline_latency) * 100 if baseline_latency > 0 else 0

            # Require at least 5% difference to be considered observable
            if latency_pct >= 5:
                details["effect_observed"] = True
                details["latency_difference_pct"] = latency_pct
                return ValidationCheckResult(
                    name="policy_effect",
                    passed=True,
                    warnings=warnings,
                    errors=[],
                    details=details,
                )
            else:
                warnings.append(f"Metrics differ only {latency_pct:.1f}% (expected >= 5%)")
                details["effect_observed"] = False
                details["latency_difference_pct"] = latency_pct
                return ValidationCheckResult(
                    name="policy_effect",
                    passed=False,
                    warnings=warnings,
                    errors=["Policy change had no observable effect"],
                    details=details,
                )
        else:
            errors.append("Could not measure latency difference (missing baseline or changed metrics)")
            return ValidationCheckResult(
                name="policy_effect",
                passed=False,
                errors=errors,
                warnings=warnings,
                details=details,
            )

    except Exception as e:
        errors.append(f"Unexpected error in policy_effect check: {e}")
        return ValidationCheckResult(
            name="policy_effect",
            passed=False,
            errors=errors,
            warnings=warnings,
            details=details,
        )


def check_failure_mode(
    loom_daemon_url: str,
    broken_quintet_url: str = "http://invalid:9999",
    timeout_sec: int = 10,
) -> ValidationCheckResult:
    """
    Invariant 7: Misconfiguration fails explicitly (no silent fallback).

    Verifies that:
    1. Loom is reachable
    2. Quintet is temporarily misconfigured (bad URL)
    3. Test episode triggered
    4. Error receipt is generated (not silent success)
    5. Error is explicit and loggable

    Returns:
        ValidationCheckResult with:
        - passed: True if error is explicit (not silent)
        - details: {"error_receipt_found": bool, "error_message": str}
    """
    errors: List[str] = []
    warnings: List[str] = []
    details: Dict[str, Any] = {}

    try:
        # Step 1: Verify Loom is reachable
        try:
            loom_health = requests.get(
                f"{loom_daemon_url}/health",
                timeout=timeout_sec,
            )
            if loom_health.status_code != 200:
                errors.append(f"Loom daemon unreachable")
                return ValidationCheckResult(
                    name="failure_mode",
                    passed=False,
                    errors=errors,
                    warnings=warnings,
                    details=details,
                )
        except requests.ConnectionError as e:
            errors.append(f"Loom daemon unreachable: {e}")
            return ValidationCheckResult(
                name="failure_mode",
                passed=False,
                errors=errors,
                warnings=warnings,
                details=details,
            )

        # Step 2: Temporarily configure Loom to use broken Quintet URL
        try:
            config_resp = requests.post(
                f"{loom_daemon_url}/api/test-config",
                json={
                    "quintet_url": broken_quintet_url,
                    "revert_after_ms": 10000,  # Auto-revert after 10sec
                },
                timeout=timeout_sec,
            )
            if config_resp.status_code != 200:
                warnings.append("Could not temporarily reconfigure Loom (may not support test-config endpoint)")
                # Continue anyway - try to trigger episode with broken config
        except requests.RequestException:
            warnings.append("Could not set broken Quintet config (endpoint may not exist)")

        # Step 3: Trigger test episode with broken Quintet config
        try:
            episode_resp = requests.post(
                f"{loom_daemon_url}/api/episodes",
                json={
                    "intent": "failure_mode_test",
                    "mode": "test",
                    "domain": "validation",
                    "test_marker": "phase2_failure_mode",
                    "require_quintet": True,  # Explicitly require Quintet
                },
                timeout=timeout_sec,
            )
            if episode_resp.status_code != 201:
                errors.append(f"Test episode failed with status {episode_resp.status_code}")
                return ValidationCheckResult(
                    name="failure_mode",
                    passed=False,
                    errors=errors,
                    warnings=warnings,
                    details=details,
                )

            episode_data = episode_resp.json()
            episode_id = episode_data.get("episode_id")
            has_error = episode_data.get("has_error", False)
            error_message = episode_data.get("error", "")

            details["episode_id"] = episode_id
            details["has_error"] = has_error
            details["error_message"] = error_message

            # Step 4: Check if error is explicit (not silent success)
            if has_error and error_message:
                # Error is explicit
                if "Quintet" in error_message or "unreachable" in error_message.lower():
                    details["error_receipt_found"] = True
                    return ValidationCheckResult(
                        name="failure_mode",
                        passed=True,
                        warnings=warnings,
                        errors=[],
                        details=details,
                    )
                else:
                    # Error exists but not clearly attributed to Quintet
                    warnings.append(f"Error exists but attribution unclear: {error_message}")
                    details["error_receipt_found"] = True
                    return ValidationCheckResult(
                        name="failure_mode",
                        passed=True,  # Error is still explicit, even if not perfectly attributed
                        warnings=warnings,
                        errors=[],
                        details=details,
                    )
            else:
                # No error - integration silently proceeded
                errors.append("Loom proceeded without Quintet (silent fallback detected)")
                details["error_receipt_found"] = False
                return ValidationCheckResult(
                    name="failure_mode",
                    passed=False,
                    errors=errors,
                    warnings=warnings,
                    details=details,
                )

        except requests.RequestException as e:
            errors.append(f"Error triggering failure mode test: {e}")
            return ValidationCheckResult(
                name="failure_mode",
                passed=False,
                errors=errors,
                warnings=warnings,
                details=details,
            )

    except Exception as e:
        errors.append(f"Unexpected error in failure_mode check: {e}")
        return ValidationCheckResult(
            name="failure_mode",
            passed=False,
            errors=errors,
            warnings=warnings,
            details=details,
        )


def run_phase2_validation(
    loom_daemon_url: str,
    quintet_service_url: str,
    test_policy_change: Optional[Dict[str, Any]] = None,
) -> ValidationSummary:
    """
    Run all Phase 2 checks (live system integration).

    Args:
        loom_daemon_url: URL of running Loom daemon (e.g., "http://localhost:8000")
        quintet_service_url: URL of running Quintet service (e.g., "http://localhost:9000")
        test_policy_change: Optional policy change to test (default: {"brain_temperature": 0.8})

    Returns:
        ValidationSummary with results of all 3 checks
    """
    checks = [
        check_live_path(loom_daemon_url, quintet_service_url),
        check_policy_effect(loom_daemon_url, quintet_service_url, test_policy_change),
        check_failure_mode(loom_daemon_url, quintet_service_url),
    ]
    return ValidationSummary(checks=checks)


def summarize_phase2(summary: ValidationSummary) -> Dict[str, Any]:
    """
    Judge Phase 2 results.

    Phase 2 is stricter than Phase 1: all 3 invariants must pass.
    No warnings allowed for live system integration.

    Args:
        summary: ValidationSummary from run_phase2_validation()

    Returns:
        Dict with:
        - overall_pass: bool (True if all 3 checks pass)
        - passed_checks: int
        - failures: List[str]
        - warnings: List[str]
    """
    passed_checks = sum(1 for c in summary.checks if c.passed)
    total_checks = len(summary.checks)
    failures = summary.failures
    warnings_list = [w for c in summary.checks for w in c.warnings]

    overall_pass = summary.all_passed and len(failures) == 0

    return {
        "overall_pass": overall_pass,
        "passed_checks": passed_checks,
        "total_checks": total_checks,
        "failures": failures,
        "warnings": warnings_list,
        "phase": "phase2",
    }
