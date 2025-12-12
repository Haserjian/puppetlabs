# Phase 2 Validation Blueprint

**Status**: Ready to implement
**Pattern**: Same as Phase 1 (reusable architecture)
**Objective**: Verify Quintet actually talks to live Loom and has expected effects

---

## Overview

Phase 2 moves from "test data in a fixture" to "live system integration."

**Question answered**: Does Quintet-Loom integration work end-to-end on a running system?

### Phase 2 Invariants (Formal Statements)

#### Invariant 5: Live Loom → Quintet Call Path
```
Given: A Loom daemon configured to call Quintet
When: Executing a test episode (e.g., policy decision request)
Then:
  - At least one successful call to Quintet API/service occurs
  - Call parameters include episode_id, mode, domain, current_policy
  - Call returns a PolicyRecommendation (or equivalent)
  - A QuintetCallReceipt is recorded (time, parameters, result)
Result: PASS if >=1 call recorded; FAIL if 0 calls or all calls error
```

#### Invariant 6: Policy Change Has Observable Effect
```
Given: A known-safe test policy change (e.g., brain_temperature adjustment)
When: Running the same test episode twice (before & after change)
Then:
  - Metrics differ (latency, cost, behavior) in predicted direction
  - A PolicyChangeReceipt links cause (change) → effect (metrics)
  - Baseline run and changed run both have audit trail
Result: PASS if effect is observable and receipted; FAIL if no effect or no receipt
```

#### Invariant 7: Misconfiguration Fails Explicitly (No Silent Fallback)
```
Given: Quintet misconfigured (bad URL, invalid API key, etc.)
When: Running a test episode that requires Quintet
Then:
  - A clear error receipt is generated (not success with skipped analysis)
  - Loom daemon does NOT silently proceed without Quintet
  - Error is loggable/auditablefor debugging
Result: PASS if error is explicit and caught; FAIL if integration silently skipped
```

---

## Phase 2 Architecture

Same pattern as Phase 1:

```
quintet/validation/
├── phase1.py              # (existing)
├── phase2.py              # NEW: 3 new invariant checks
└── types.py               # (reuse existing)

scripts/
├── validate_phase_1_cli.py    # (existing)
└── validate_phase_2_cli.py    # NEW: CLI entry point
```

### Phase 2 Invariants (Code Sketch)

```python
# quintet/validation/phase2.py

from quintet.validation.types import ValidationCheckResult, ValidationSummary

def check_live_path(
    loom_daemon_url: str,
    quintet_service_url: str,
    test_episode_intent: str = "test_policy_evaluation",
) -> ValidationCheckResult:
    """
    Invariant 5: Live Loom → Quintet call path exists.

    1. Trigger a test episode via Loom daemon
    2. Assert Quintet receives and processes the call
    3. Record call metadata
    """
    # Pseudo-code:
    # episode = loom.trigger_episode(intent=test_episode_intent)
    # calls = quintet.api.get_calls(since=now-5sec, episode_id=episode.id)
    # return PASS if len(calls) >= 1 else FAIL
    ...


def check_policy_effect(
    loom_daemon_url: str,
    quintet_service_url: str,
    test_policy_change: Dict[str, Any],  # e.g., {"brain_temperature": 0.8}
) -> ValidationCheckResult:
    """
    Invariant 6: Policy change has observable effect.

    1. Run test episode (baseline)
    2. Apply policy change
    3. Run same test episode again
    4. Assert metrics differ in expected direction
    5. Assert receipts link change → effect
    """
    # Pseudo-code:
    # baseline = run_and_measure(loom, quintet, "before_change")
    # apply_policy_change(test_policy_change)
    # changed = run_and_measure(loom, quintet, "after_change")
    # assert metrics_differ(baseline, changed)
    # assert receipt_links_cause_effect(...)
    ...


def check_failure_mode(
    loom_daemon_url: str,
    broken_quintet_url: str = "http://invalid:9999",  # intentionally broken
) -> ValidationCheckResult:
    """
    Invariant 7: Misconfiguration fails explicitly.

    1. Temporarily break Quintet config (bad URL)
    2. Run a test episode
    3. Assert error is explicit (not silent fallback)
    4. Assert error receipt is recorded
    """
    # Pseudo-code:
    # with temporarily_misconfigured_quintet(broken_quintet_url):
    #     episode = loom.trigger_episode(intent="test")
    #     assert episode.has_error_receipt
    #     assert "Quintet unreachable" in error_receipt.reason
    ...


def run_phase2_validation(
    loom_daemon_url: str,
    quintet_service_url: str,
) -> ValidationSummary:
    """Run all Phase 2 checks."""
    checks = [
        check_live_path(loom_daemon_url, quintet_service_url),
        check_policy_effect(loom_daemon_url, quintet_service_url, {...}),
        check_failure_mode(loom_daemon_url),
    ]
    return ValidationSummary(checks=checks)


def summarize_phase2(summary: ValidationSummary) -> Dict[str, Any]:
    """Judge Phase 2 results."""
    # Same shape as Phase 1, but possibly stricter:
    # Phase 2 passes only if ALL 3 invariants pass (no warnings allowed for live system)
    overall_pass = summary.all_passed and len(summary.failures) == 0
    ...
```

---

## Phase 2 CLI (Sketch)

```python
# scripts/validate_phase_2_cli.py

from quintet.validation.phase2 import run_phase2_validation, summarize_phase2
from quintet.causal.validation_receipts import create_phase2_receipt
from quintet.causal.receipt_persistence import ReceiptStore

def main(argv=None) -> int:
    # 1. Read config or args to get Loom/Quintet URLs
    loom_url = os.getenv("LOOM_DAEMON_URL", "http://localhost:8000")
    quintet_url = os.getenv("QUINTET_SERVICE_URL", "http://localhost:9000")

    # 2. Run validation
    summary = run_phase2_validation(loom_url, quintet_url)
    result = summarize_phase2(summary)

    # 3. Print results (same format as Phase 1)
    for check in summary.checks:
        print(f"{'✅' if check.passed else '❌'} {check.name}")

    # 4. Mint Phase2ValidationReceipt
    receipt = create_phase2_receipt(
        loom_profile="local-test",
        loom_config_hash=compute_hash(loom_url),
        quintet_config_hash=compute_hash(quintet_url),
        checks={c.name: c.passed for c in summary.checks},
        warnings=[w for c in summary.checks for w in c.warnings],
        failures=result["failures"],
        quintet_calls_observed=...,  # from metrics
        policy_changes_applied=...,  # from metrics
    )

    # 5. Persist receipt
    store = ReceiptStore()
    store.append_receipt(receipt)

    return 0 if result["overall_pass"] else 1
```

---

## Test Fixtures Needed for Phase 2

Unlike Phase 1 (which uses static JSON), Phase 2 needs:

### 1. Loom Test Profile
A minimal Loom daemon config for testing:
```yaml
# config/loom_test_profile.yaml
daemon:
  port: 8765  # non-standard port
  mode: test
  log_level: debug

quintet:
  service_url: http://localhost:9000
  timeout_sec: 5
  retry_policy: none  # fail fast on error
```

### 2. Quintet Test Service Config
```yaml
# config/quintet_test_service.yaml
port: 9000
ephemeral: true  # don't persist receipts
validation_mode: true  # emit extra diagnostics
```

### 3. Test Episode Definitions
```python
# tests/phase2_episodes.py
TEST_EPISODES = {
    "policy_evaluation": {
        "intent": "decide brain_temperature",
        "current_policy": {"brain_temperature": 0.7},
        "expected_recommendation": {"action": "HOLD", "min_confidence": 0.5},
    },
    "resource_change": {
        "intent": "adjust resource limits",
        "policy_change": {"max_tokens": 5000},
        "baseline_metric": "latency_ms",
        "expected_direction": "decrease",
    },
}
```

---

## Implementation Roadmap

### Week 1: Infrastructure
- [ ] Create `quintet/validation/phase2.py` skeleton
- [ ] Implement `check_live_path()` (verify Quintet call occurs)
- [ ] Add logging/tracing to Loom daemon for call tracking
- [ ] Create test fixtures (Loom/Quintet configs)

### Week 2: Core Checks
- [ ] Implement `check_policy_effect()` (baseline vs changed metrics)
- [ ] Add A/B test harness to Loom for running same episode twice
- [ ] Implement `check_failure_mode()` (misconfiguration error handling)
- [ ] Wire Phase2ValidationReceipt creation

### Week 3: CLI & Integration
- [ ] Create `scripts/validate_phase_2_cli.py`
- [ ] Integrate receipt minting (like Phase 1)
- [ ] Run full Phase 2 validation on test system
- [ ] Document any integration gaps found

### Week 4: Polish & Docs
- [ ] Fix any bugs from full runs
- [ ] Document test setup/teardown
- [ ] Create Phase 2 report (same format as Phase 1)
- [ ] Plan Phase 3 based on Phase 2 results

---

## Success Criteria

Phase 2 is complete when:

✅ Invariant 5: Live Loom → Quintet calls are recorded and auditable
✅ Invariant 6: Policy changes have observable, receipted effects
✅ Invariant 7: Misconfiguration produces explicit errors (not silent fallback)
✅ Phase2ValidationReceipt minted with all metadata
✅ CLI runs cleanly on test system
✅ All 3 checks pass

---

## Failure Modes to Watch For

1. **Silent Integration Failure**: Loom proceeds without Quintet, pretends it worked
   → Fix: Invariant 7 catches this (explicitly check for error)

2. **Metrics Noise Masking Effect**: Effect exists but is too small to detect reliably
   → Fix: Use A/B test harness with multiple runs, aggregate metrics

3. **Receipt Decay**: Calls are recorded but receipts aren't persisted/retrievable
   → Fix: Persist Phase2ValidationReceipt, verify round-trip

4. **Timeout Sensitivity**: Quintet is slow; integration appears broken when it's just slow
   → Fix: Make timeouts configurable, log latency metrics

---

## Phase 2 → Phase 3 Transition

Once Phase 2 passes:

- Phase 3 takes a sample of 10 real recommendations from Phase 2 runs
- Traces causal reasoning for each
- Scores on confidence, robustness, safety
- Documents any biases/confounding

Same pattern; new invariants.

---

## Files to Create

| File | Purpose | Est. Lines |
|------|---------|-----------|
| `quintet/validation/phase2.py` | Invariant functions | 400 |
| `scripts/validate_phase_2_cli.py` | CLI entry point | 120 |
| `tests/phase2_episodes.py` | Test episode fixtures | 100 |
| `tests/phase2_test_harness.py` | A/B test runner | 200 |
| `config/loom_test_profile.yaml` | Loom config | 30 |
| `config/quintet_test_service.yaml` | Quintet config | 20 |
| `PHASE_2_REPORT.md` | Results summary | 200 |

**Total**: ~1,070 lines of new code + docs

---

## Integration with Phase 1

Phase 2 depends on Phase 1 passing:

```
Phase 1 PASSED ✅
  ↓
Phase 1ValidationReceipt minted
  ↓
Phase 2 runs (checks live system)
  ↓
Phase 2ValidationReceipt minted
  ↓
(Both receipts form an audit trail)
```

---

## Notes for Implementation

1. **Loom/Quintet Communication**: Phase 2 needs direct access to call logs. Plan how to expose this:
   - Option A: HTTP endpoint `/api/calls` on Quintet
   - Option B: Shared JSON log file
   - Option C: Tracing system (OpenTelemetry) both systems publish to

2. **Metrics Collection**: Need to measure episode latency, cost, behavior before/after. Plan storage:
   - Option A: Loom episodes include `metrics` field
   - Option B: Separate metrics service
   - Option C: Extract from logs

3. **A/B Test Safety**: Must ensure test episodes don't corrupt production state:
   - Use test domain/mode
   - Clean up after each run
   - Document rollback procedure

4. **Timeouts**: Network calls to Quintet may be slow. Set appropriate timeouts:
   - Connect: 5 sec
   - Read: 10 sec
   - Total: 30 sec

---

**Next**: Once Phase 2 is ready to implement, refer back to this blueprint and follow the same pattern as Phase 1.

**Estimated Implementation Time**: 2-3 weeks (including infrastructure setup + testing)
