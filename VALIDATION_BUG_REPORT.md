# Validation Run - Bug Report

**Date:** 2025-12-09
**Status:** 3 integration bugs found

---

## Bug #1: Missing `reasoning` attribute

**Location:** `quintet/loom_adapter.py:PolicyRecommendation`

**Issue:**
```python
# Validation script tried to access:
rec.reasoning  # ❌ Doesn't exist

# What exists:
rec.evidence  # ✅ Dict with causal analysis
```

**Fix:** Use `evidence` field instead of `reasoning`

---

## Bug #2: Wrong import path

**Location:** `quintet/stress/run_pre_promote_check.py` (doesn't exist)

**Issue:**
```python
# Script tried:
from quintet.stress.run_pre_promote_check import run_pre_promote_check  # ❌

# Actual file:
quintet/stress/run_pre_promote.py  # ✅
```

**Fix:** Correct import path (also check function name)

---

## Bug #3: Test Data Size Discrepancy

**Status:** Minor
**Issue:** Fixture JSON metadata says 45 episodes, actual file contains 15
**Fix:** Either update fixture or metadata

---

## What Works

✅ Episode loading from JSON
✅ Episode stratification by mode/domain
✅ Basic structure of recommendation objects
✅ All 22 unit tests pass (but they don't validate against actual code)

---

## What Needs Fixing

These bugs need to be fixed before Phase 1 can complete:

1. [ ] Update `validate_phase_1.py` to use `evidence` instead of `reasoning`
2. [ ] Verify actual filename for pre-promotion check module
3. [ ] Fix import statement in validation script
4. [ ] Re-run validation to see if there are more bugs

---

## Next Step

Run the corrected validation script after fixes applied.

