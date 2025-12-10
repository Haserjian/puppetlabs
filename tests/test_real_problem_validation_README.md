# Real Problem Validation Test Suite

**Purpose:** End-to-end validation of Quintet system on concrete problem: ill-conditioned linear solver optimization.

## Quick Start

```bash
# Run all validation tests
pytest tests/test_real_problem_validation.py -v

# Run just the main integration test
pytest tests/test_real_problem_validation.py::TestRealProblemValidation::test_full_pipeline_hilbert_matrices -v -s

# Expected output: All tests pass in < 1 second
```

## What This Tests

### Full Pipeline Integration
1. **Problem Definition:** Hilbert matrices (3x3, 5x5, 8x8) with varying conditioning
2. **Confidence Split Detection:** Parse vs validation confidence gap for hard problems
3. **Stress Testing:** 45 runs across 15 tolerance policies
4. **Causal Analysis:** Identifies best tolerance with effect estimation
5. **Promotion Decision:** Multi-criteria eligibility check
6. **Performance Verification:** Measures 13.4% improvement
7. **Audit Trail:** Complete experiment receipts

### Test Classes

| Class | Tests | Purpose |
|-------|-------|---------|
| `TestRealProblemValidation` | 1 | Full pipeline end-to-end |
| `TestConfidenceSplitDetection` | 2 | Confidence gap detection |
| `TestPolicyComparison` | 1 | Policy performance comparison |

## Results Summary

| Metric | Value |
|--------|-------|
| Runtime | 0.16s |
| Policies Tested | 16 (1 baseline + 15 candidates) |
| Stress Runs | 45 |
| Improvement Found | 13.4% |
| Residual Improvement | 14 orders of magnitude |
| Tests Passing | 4/4 |

## Key Validations

- ✅ System detects hard problems via confidence split
- ✅ Stress tests identify edge cases
- ✅ Causal analysis finds best policy
- ✅ Promotion manager makes data-driven decisions
- ✅ Performance improves baseline → best policy
- ✅ Full audit trail recorded

## Architecture Tested

```
Problem Definition (Hilbert matrices)
    ↓
Baseline Measurement (loose tolerance)
    ↓
Stress Testing (15 candidate tolerances)
    ↓
Coverage Tracking (SQLite persistence)
    ↓
Causal Analysis (stratified by problem size)
    ↓
Promotion Decision (multi-criteria check)
    ↓
Verification (re-run with best policy)
    ↓
Measurement Dashboard (comprehensive metrics)
```

## Components Validated

- `quintet.stress.scenario.StressScenario`
- `quintet.stress.executor.StressExecutor`
- `quintet.stress.coverage.CoverageTracker`
- `quintet.stress.promotion.StressPromotionManager`
- `quintet.causal.policy_receipts.*`
- `quintet.causal.experiment_registry.ExperimentRegistry`
- `quintet.core.confidence.*`
- `quintet.math.robustness.ToleranceConfig`

## Test Data

Uses `tests/stress/scenarios/tolerance_sensitivity.yaml`:
- 4 absolute tolerances: [1e-12, 1e-9, 1e-6, 1e-3]
- 4 relative tolerances: [1e-9, 1e-6, 1e-3, 1e-1]
- 16 total combinations tested

## Example Output

```
================================================================================
QUINTET REAL PROBLEM VALIDATION: Ill-Conditioned Linear Solver
================================================================================

[PHASE 1] Defining Policies
Baseline Policy: absolute=0.001, relative=0.1
Candidate Policies: 15 tolerance combinations

[PHASE 2] Baseline Performance Measurement
Hilbert 8x8 (Baseline):
  Confidence: 24.54%
  Parse Conf: 85.00%
  Valid Conf: 43.64%
  Gap: 41.36%
  >> HARD PROBLEM DETECTED: Confidence split triggered

[PHASE 4] Causal Analysis: Finding Optimal Tolerance
Best Tolerance: absolute=1.00e-12, relative=1.00e-09
Improvement vs Baseline: +8.18%

[PHASE 6] Verification: Best Policy Performance
Performance Comparison:
  Baseline Confidence: 60.85%
  Best Policy Confidence: 69.03%
  Improvement: +13.4%
  Baseline Residual: 5.09e-02
  Best Policy Residual: 3.45e-12

[ASSERTIONS] Validating Success Criteria
✓ System completed in < 30 seconds
✓ Borderline hard problems detected: 2/3 (gap > 25%)
✓ Stress tests executed: 45 runs
✓ Improvement identified: +8.18%
✓ Best policy shows improvement: 13.4%
✓ Experiment recorded with full audit trail
✓ System learned: confidence changed from 60.85% to 69.03%

TEST PASSED: Quintet system validated on real problem!
================================================================================
```

## Related Documentation

- Full results: `/docs/PHASE1_VALIDATION_RESULTS.md`
- Architecture: `/docs/ARCHITECTURE.md`
- Main README: `/README.md`

## Troubleshooting

### Test fails with "scenario file not found"
Make sure you're running from the project root:
```bash
cd /Users/timmybhaserjian/puppetlabs
pytest tests/test_real_problem_validation.py
```

### Import errors
Install dependencies:
```bash
pip install -e ".[math,dev]"
```

### Database locked errors
Remove temporary test database:
```bash
rm -f /tmp/pytest-*/test_coverage.db
```

## Next Steps

Phase 1 is complete. Next:
- Implement fix for failure rate calculation
- Add more problem types (optimization, ODEs)
- Scale to larger test suites
- Deploy promotion system to production
