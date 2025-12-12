# Phase 2 Implementation Guide

**Status**: Ready to Test
**Date**: 2025-12-10
**Version**: 1.0 (Core Implementation Complete)

---

## Overview

Phase 2 validates live Loom ↔ Quintet integration on a running system. This implementation provides:

- ✅ **Core Library** (`quintet/validation/phase2.py`) – 3 invariant checks
- ✅ **CLI Entry Point** (`scripts/validate_phase_2_cli.py`) – Clean interface with receipt minting
- ✅ **Test Fixtures** (`tests/fixtures/phase2_test_episodes.py`) – Episode definitions & configurations
- ✅ **Receipt Support** – Mints `Phase2ValidationReceipt` on each run

---

## Running Phase 2 Validation

### Prerequisites

1. **Loom daemon** running at `http://localhost:8000` (or specify with `--loom-url`)
2. **Quintet service** running at `http://localhost:9000` (or specify with `--quintet-url`)
3. Both services should have **test/validation mode** enabled
4. **Python environment** with quintet package installed

### Basic Usage

```bash
# Run Phase 2 validation with defaults
python3 scripts/validate_phase_2_cli.py

# With custom URLs
python3 scripts/validate_phase_2_cli.py \
    --loom-url http://localhost:8765 \
    --quintet-url http://localhost:9000

# With environment variables
export LOOM_DAEMON_URL="http://localhost:8765"
export QUINTET_SERVICE_URL="http://localhost:9000"
python3 scripts/validate_phase_2_cli.py
```

### Output Example

```
======================================================================
Phase 2 Validation: Live Loom ↔ Quintet Integration
======================================================================

Testing Loom: http://localhost:8000
Testing Quintet: http://localhost:9000

Invariant Checks:

✅ live_path
✅ policy_effect
✅ failure_mode

3/3 checks passed

✅ Phase 2 VALIDATION PASSED

📜 Validation receipt minted: bc467d86-fef1-4b07-9cb3-0ca988b82771
   Stored in: .quintet_validation_receipts/phase2_receipts.jsonl
```

### Exit Codes

- **0**: Phase 2 PASSED (all 3 invariants satisfied)
- **1**: Phase 2 FAILED (one or more invariants not satisfied)

---

## The Three Invariants

### Invariant 5: Live Loom → Quintet Call Path Exists

**Question**: Can Loom actually call Quintet and get a response?

**What it checks**:
1. Loom daemon is reachable and healthy
2. Quintet service is reachable and healthy
3. Can trigger a test episode via Loom
4. Quintet service logs the call
5. Call parameters are well-formed
6. Response is a valid PolicyRecommendation

**Success Criteria**: ≥1 successful call recorded in Quintet call logs

**Common Failures**:
- Loom daemon not running → "Loom daemon unreachable at ..."
- Quintet service not running → "Quintet service unreachable at ..."
- Network misconfiguration → Connection timeout
- Loom can't reach Quintet → "No Quintet calls recorded"

### Invariant 6: Policy Change Has Observable Effect

**Question**: When we change a policy, do the results actually differ?

**What it checks**:
1. Record baseline metrics (episode with current policy)
2. Apply a known-safe policy change
3. Run same episode again with new policy
4. Verify metrics differ (latency, confidence, outcome)
5. Difference is > 5% to count as "observable"

**Success Criteria**: Observable metric difference in predicted direction

**Common Failures**:
- Insufficient metric difference → "Metrics differ only 2.3% (expected >= 5%)"
- Policy change not applied → No difference observed
- Metrics not captured → Missing latency/confidence data

### Invariant 7: Misconfiguration Fails Explicitly (No Silent Fallback)

**Question**: If Quintet is broken, does the system fail loudly or silently skip?

**What it checks**:
1. Loom daemon is reachable
2. Temporarily break Quintet config (bad URL)
3. Trigger test episode requiring Quintet
4. Verify episode fails with explicit error
5. Error mentions Quintet (not generic failure)

**Success Criteria**: Error receipt generated (not silent success)

**Common Failures**:
- Loom proceeds without Quintet → "Loom proceeded without Quintet (silent fallback detected)"
- Error exists but unclear → Warning that attribution is unclear (but still passes)
- No error at all → Silent fallback detected

---

## Understanding the Library

### Core Functions

```python
# Main entry point
from quintet.validation import run_phase2_validation, summarize_phase2

summary = run_phase2_validation(
    loom_daemon_url="http://localhost:8000",
    quintet_service_url="http://localhost:9000",
    test_policy_change={"brain_temperature": 0.8},
)

result = summarize_phase2(summary)

# Check results
if result["overall_pass"]:
    print("✅ Phase 2 PASSED")
else:
    print("❌ Phase 2 FAILED")
    for failure in result["failures"]:
        print(f"  • {failure}")
```

### Individual Checks

```python
from quintet.validation import check_live_path, check_policy_effect, check_failure_mode

# Check live path
result1 = check_live_path(
    loom_daemon_url="http://localhost:8000",
    quintet_service_url="http://localhost:9000",
)
print(f"Live path: {'PASS' if result1.passed else 'FAIL'}")
print(f"  Calls observed: {result1.details.get('calls_observed', 0)}")

# Check policy effect
result2 = check_policy_effect(
    loom_daemon_url="http://localhost:8000",
    quintet_service_url="http://localhost:9000",
    test_policy_change={"brain_temperature": 0.8},
)

# Check failure mode
result3 = check_failure_mode(
    loom_daemon_url="http://localhost:8000",
    broken_quintet_url="http://invalid:9999",
)
```

### Receipt Structure

Each validation run mints a `Phase2ValidationReceipt`:

```python
{
    "receipt_id": "abc123...",
    "timestamp": "2025-12-10T10:30:00",
    "phase": "phase2",
    "passed": true,
    "checks": {
        "live_path": true,
        "policy_effect": true,
        "failure_mode": true
    },
    "warnings": [],
    "failures": [],
    "loom_profile": "local-test",
    "loom_config_hash": "d42761b9...",
    "quintet_config_hash": "744bc3cd...",
    "check_live_path": true,
    "check_policy_effect": true,
    "check_failure_mode": true,
    "quintet_calls_observed": 3,
    "policy_changes_applied": 1,
    "receipt_hash": "7ae3502cdc...",
    "parent_hash": "744bc3cd...",  # Links to Phase 1 receipt
    "sequence_number": 1
}
```

### Querying Receipts

```python
from quintet.causal.receipt_persistence import ReceiptStore

store = ReceiptStore(".quintet_validation_receipts/phase2_receipts.jsonl")
receipts = store.read_all_receipts()

for receipt in receipts:
    print(f"Phase: {receipt.receipt.phase}")
    print(f"Passed: {receipt.receipt.passed}")
    print(f"Checks: {receipt.receipt.checks}")
```

---

## Integrating with Your Systems

### Loom Integration

Phase 2 expects Loom to support these endpoints:

**Health Check**:
```
GET /health
Response: {"status": "healthy"} (200 OK)
```

**Create Test Episode**:
```
POST /api/episodes
Body: {
    "intent": str,
    "mode": "test",
    "domain": str,
    "test_marker": str,
    "require_quintet": bool (optional)
}
Response: {
    "episode_id": str,
    "latency_ms": float,
    "confidence": float,
    "outcome": "success|failure|degraded",
    "has_error": bool (optional),
    "error": str (optional)
}
```

**Test Configuration** (optional):
```
POST /api/test-config
Body: {
    "quintet_url": str,
    "revert_after_ms": int
}
Response: {"success": true} (200 OK)
```

### Quintet Integration

Phase 2 expects Quintet to support these endpoints:

**Health Check**:
```
GET /health
Response: {"status": "healthy"} (200 OK)
```

**Query Calls**:
```
GET /api/calls?episode_id=xyz&since=timestamp
Response: {
    "calls": [
        {
            "call_id": str,
            "episode_id": str,
            "parameters": {...},
            "result": {...},
            "duration_ms": float,
            "success": bool
        }
    ]
}
```

**Test Policy Change** (optional):
```
POST /api/test-policy-change
Body: {
    "change": {
        "brain_temperature": 0.8,
        ...
    },
    "revert_after_ms": int
}
Response: {"success": true} (200 OK)
```

---

## Troubleshooting

### Phase 2 Won't Run

**Problem**: "Loom daemon unreachable"

**Solutions**:
1. Check Loom is running: `curl http://localhost:8000/health`
2. Verify port (default 8000, override with `--loom-url`)
3. Check firewall/network connectivity
4. Ensure Loom is in test/validation mode

**Problem**: "Quintet service unreachable"

**Solutions**:
1. Check Quintet is running: `curl http://localhost:9000/health`
2. Verify port (default 9000, override with `--quintet-url`)
3. Check firewall/network connectivity
4. Ensure Quintet is in test/validation mode

### Invariant 5 Fails

**Problem**: "No Quintet calls recorded"

**Solutions**:
1. Verify Loom can reach Quintet: Check Loom's config
2. Enable call logging in Quintet: Ensure `/api/calls` endpoint exists
3. Add test marker to episodes: Phase 2 uses `test_marker` to identify calls
4. Increase timeout: Use `--timeout 20` to allow more time for propagation

### Invariant 6 Fails

**Problem**: "Metrics differ only 2.3% (expected >= 5%)"

**Solutions**:
1. Use a more significant policy change (larger value change)
2. Check that policy change was actually applied (verify in logs)
3. Increase baseline_delay_sec (allow more time for change to take effect)
4. Use a domain where policy changes have larger impact

**Problem**: "Could not measure latency difference"

**Solutions**:
1. Verify episodes return latency_ms field
2. Check Loom is measuring episode duration
3. Ensure episodes are actually being executed (not skipped)

### Invariant 7 Fails

**Problem**: "Loom proceeded without Quintet (silent fallback detected)"

**Solutions**:
1. Verify Loom requires Quintet for test episodes (set `require_quintet: true`)
2. Check Loom's error handling: Should NOT silently skip Quintet
3. Enable strict mode in Loom: No fallbacks for missing Quintet
4. Verify `/api/test-config` endpoint if Loom supports it

---

## Next Steps

### Once Phase 2 Passes

1. **Commit receipt**: `git add .quintet_validation_receipts/phase2_receipts.jsonl`
2. **Document**: Create `PHASE_2_REPORT.md` (same format as PHASE_1_REPORT.md)
3. **Archive**: Save receipt for future reference
4. **Plan Phase 3**: Quality assessment of recommendations

### Phase 2 → Phase 3

Once Phase 2 passes:

- Phase 2 proves: Quintet-Loom integration works
- Phase 3 will ask: Are the recommendations *good*?
- Phase 3 will sample recommendations and score them
- Use Phase 2 receipts as proof of integration stability

---

## Files Reference

| File | Purpose |
|------|---------|
| `quintet/validation/phase2.py` | Core library (3 checks) |
| `scripts/validate_phase_2_cli.py` | CLI entry point (with receipt minting) |
| `tests/fixtures/phase2_test_episodes.py` | Test episode definitions |
| `.quintet_validation_receipts/phase2_receipts.jsonl` | Receipt storage (JSONL) |

---

## FAQ

**Q: Can I run Phase 2 without Phase 1?**
A: Yes. Phase 2 is independent (tests live system). Phase 1 is pre-requisite only in that it proves test fixtures work.

**Q: How long does Phase 2 take?**
A: ~30-60 seconds total (depends on network latency and episode execution time).

**Q: Can I customize the test policy change?**
A: Yes: `--policy-change '{"brain_temperature": 0.9}'`

**Q: What if Loom/Quintet are on different machines?**
A: Set `--loom-url` and `--quintet-url` to full URLs: `http://192.168.1.10:8000`

**Q: How do I know Phase 2 passed?**
A: Look for "✅ Phase 2 VALIDATION PASSED" and exit code 0.

**Q: Can Phase 2 break production?**
A: No. Phase 2 uses test mode exclusively. Episodes are marked with `mode: "test"`.

---

## Architecture Notes

### Why Three Invariants?

1. **Invariant 5** (Live Path): Proves the connection works
2. **Invariant 6** (Policy Effect): Proves policies actually matter
3. **Invariant 7** (Failure Mode): Proves safety gates work

Together, they answer: "Does Quintet-Loom integration work end-to-end?"

### Why HTTP-based?

Phase 2 assumes Loom and Quintet are deployed as services with HTTP APIs. This is typical for:
- Development/testing environments (localhost)
- Staging deployments
- Production systems with service architecture

If your system uses IPC/RPC instead, modify the check functions to use your communication layer.

### Why Receipts?

Receipts enable:
- Audit trail (who validated what, when)
- Chaining (Phase 2 receipt links to Phase 1)
- Replay (re-run validation, compare receipts)
- Evidence (proof for production deployment)

---

**Status**: 🟢 Ready to Test
**Next**: Run Phase 2 on your live system
**Report**: Create `PHASE_2_REPORT.md` after first run

---

*Created: 2025-12-10*
*Version: 1.0 (Core Implementation)*
