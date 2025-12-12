# Quintet Validation System

Quick navigation for the validation framework.

## Running Validation

```bash
# Run Phase 1 validation
python3 scripts/validate_phase_1_cli.py

# Or the legacy wrapper (still works)
python3 scripts/validate_phase_1.py
```

Expected output:
```
✅ episode_quality
✅ recommendations
⚠️ stress_gates (CLI-only, not importable)
✅ receipt_chain

3/4 checks passed
✅ Phase 1 VALIDATION PASSED
```

Exit code: 0 (passed), 1 (failed)

---

## Documentation Files

### Overview
- **[QUINTET_VALIDATION_SUMMARY.md](./QUINTET_VALIDATION_SUMMARY.md)** ← START HERE
  - Complete overview of what was built
  - Quick links to all docs
  - Results summary

### Architecture & Design
- **[VALIDATION_ARCHITECTURE.md](./VALIDATION_ARCHITECTURE.md)**
  - System design and principles
  - How to extend to Phase 2+
  - Testing patterns

- **[PHASE_1_1_REFACTOR_SUMMARY.md](./PHASE_1_1_REFACTOR_SUMMARY.md)**
  - What changed in the refactor
  - Before/after comparison
  - Explicit state for safety gates

### Results & Status
- **[PHASE_1_REPORT.md](./PHASE_1_REPORT.md)**
  - Detailed Phase 1 validation results
  - Bugs found and fixed
  - Recommendations

- **[VALIDATION_STATUS.md](./VALIDATION_STATUS.md)**
  - Executive summary dashboard
  - Phase 1-4 status
  - What's next

- **[VALIDATION_FRAMEWORK.md](./VALIDATION_FRAMEWORK.md)**
  - Overall validation strategy (8-day roadmap)
  - Phase breakdown
  - Critical unknowns

---

## Code Files

### Library (Reusable)
```
quintet/validation/
├── __init__.py              # Public API
├── types.py                 # ValidationCheckResult, ValidationSummary
└── phase1.py                # 4 invariant checks + runners
```

### CLI Entry Points
```
scripts/
├── validate_phase_1_cli.py  # New recommended entry point
└── validate_phase_1.py      # Legacy wrapper (backward compat)
```

---

## Using in Code

### Import and run
```python
from quintet.validation.phase1 import run_phase1_validation, summarize_phase1
import json

episodes = json.loads(Path("episodes.json").read_text())["episodes"]

# Run validation
summary = run_phase1_validation(episodes)

# Get results
result = summarize_phase1(summary)
print(f"Phase 1: {'PASSED' if result['overall_pass'] else 'FAILED'}")

# Or inspect individual checks
for check in summary.checks:
    print(f"{check.name}: {check.passed}")
```

### In tests
```python
from quintet.validation.phase1 import check_episode_quality

def test_episode_schema():
    episodes = load_fixtures()
    result = check_episode_quality(episodes)
    assert result.passed
```

---

## What Each Check Does

### 1. episode_quality
Verifies episode export is structurally sound:
- Episodes can be parsed as LoomEpisode objects
- Required fields are present
- No malformed data

✅ **Result**: PASS

### 2. recommendations
Validates Quintet analysis produces coherent recommendations:
- Analyzer runs without throwing
- Average confidence >= 0.6
- Returns per-lever scores

✅ **Result**: PASS (confidence: 0.62)

### 3. stress_gates
Checks pre-promotion safety gates exist:
- CLI script: ✅ exists
- Importable API: ❌ not yet

⚠️ **Result**: WARN (CLI-only, not importable)

### 4. receipt_chain
Verifies policy change receipts work end-to-end:
- Construct PolicyIntervention + PolicyExperiment + PolicyChangeReceipt
- Compute SHA256 hash
- Persist via ReceiptStore
- Reload and verify hash stability

✅ **Result**: PASS (hash stable, persistence works)

---

## Phase 1 Results Summary

| Check | Result | Status |
|-------|--------|--------|
| Episode Quality | PASS | ✅ |
| Recommendations | PASS | ✅ |
| Stress Gates | WARN | ⚠️ |
| Receipt Chain | PASS | ✅ |
| **Overall** | **3/4 PASSED** | **✅** |

---

## Next Steps: Phase 2

To build Phase 2, follow the pattern:

1. Create `quintet/validation/phase2.py`
2. Implement invariant checks:
   - check_loom_daemon_integration()
   - check_policy_application()
   - check_outcome_measurement()
   - etc.
3. Create `run_phase2_validation()` and `summarize_phase2()`
4. Create `scripts/validate_phase_2_cli.py`
5. Reuse `ValidationCheckResult` and `ValidationSummary` types

---

## Key Design Principles

1. **Invariants are named functions** (not magic numbers)
2. **Results are structured** (not textual)
3. **Judgment sits in the CLI** (library is reusable)
4. **Safety gates are explicit** (not hidden in heuristics)
5. **No model branding** (pure infrastructure)

---

## Files Quick Reference

| File | Purpose | Lines |
|------|---------|-------|
| quintet/validation/types.py | Shared types | 130 |
| quintet/validation/phase1.py | Invariants | 380 |
| quintet/validation/__init__.py | Public API | 30 |
| scripts/validate_phase_1_cli.py | CLI entry | 100 |
| scripts/validate_phase_1.py | Legacy wrapper | 40 |

**Total**: ~680 lines of clean, reusable validation code

---

## Troubleshooting

### Import error: No module named 'quintet'
Run from the project root directory:
```bash
cd /Users/timmybhaserjian/puppetlabs
python3 scripts/validate_phase_1_cli.py
```

### Script errors
Check `details` in the `ValidationCheckResult`:
```python
from quintet.validation.phase1 import run_phase1_validation

summary = run_phase1_validation(episodes)
for check in summary.checks:
    if not check.passed:
        print(f"{check.name}: {check.errors}")
        print(f"Details: {check.details}")
```

---

## Status

✅ Phase 1: COMPLETE (validation passes)
✅ Phase 1.1: COMPLETE (architecture refactored)
⏳ Phase 2: READY TO START (pattern established)
⏳ Phase 3: READY TO PLAN
⏳ Phase 4: READY TO PLAN

**Next**: Phase 2 integration testing

---

Last updated: 2025-12-09
Version: 1.0 (Phase 1.1 Complete)
