# Quintet Validation Architecture

**Version**: 1.0
**Status**: Phase 1.1 refactored (clean, extensible, no model branding)

---

## Overview

The validation system is now a proper, composable organism instead of a monolithic script.

**Principle**: Each validation phase is a set of **named invariants** that return structured results. This allows:
- Programmatic consumption by other systems (not just console output)
- Reuse across Phase 1, 2, 3, etc.
- Clear reasoning about what "passed" means
- Easy addition to CI/CD pipelines or automated decision systems

---

## Architecture

```
quintet/validation/
├── __init__.py          # Public API exports
├── types.py             # ValidationCheckResult, ValidationSummary
└── phase1.py            # Phase 1 invariants (4 checks)

scripts/
├── validate_phase_1.py           # Legacy wrapper (for backward compat)
└── validate_phase_1_cli.py       # New thin CLI entry point
```

### Data Flow

```
Fixture JSON
    ↓
validate_phase_1_cli.py (entry point)
    ↓
run_phase1_validation(episodes)     [library function]
    ├─ check_episode_quality()       → ValidationCheckResult
    ├─ check_recommendations()       → ValidationCheckResult
    ├─ check_stress_gates()          → ValidationCheckResult
    └─ check_receipt_chain()         → ValidationCheckResult
    ↓
ValidationSummary (aggregates 4 results)
    ↓
summarize_phase1(summary)            [judgment function]
    ↓
CLI pretty-prints + exits
```

---

## Phase 1 Invariants (Formal Statements)

These are the "physics" that Phase 1 validates. Written as testable claims, not prose.

### Invariant 1: Episode Export Structure
```
Given: A JSON export from Loom (loom_export_sample.json)
When: Loading episodes as LoomEpisode objects
Then:
  - episode_count >= 1 (non-empty)
  - ∀ episode: episode_id ∈ {id, episode_id}
  - ∀ episode: mode ∈ {council, guardian, brain, unknown}
  - ∀ episode: outcome ∈ {success, failure, partial}
  - ∀ episode: policy is a dict with keys {brain_temperature, guardian_strictness, perception_threshold}
Result: PASS if all parse successfully; FAIL if any required field missing or type error
```

### Invariant 2: Recommendation Coherence
```
Given: Parsed LoomEpisode list (from Invariant 1)
When: Running analyze_episodes(episodes, lever=L) for L ∈ {brain_temperature, guardian_strictness, perception_threshold}
Then:
  - All three analyses complete without exception
  - Each returns PolicyRecommendation with action ∈ {PROMOTE, HOLD, ROLLBACK}
  - confidence is in [0.0, 1.0] and >= 0.60
  - average(confidence across 3 levers) >= 0.60
Result: PASS if avg >= 0.6 and no errors; FAIL if any analysis throws or avg < 0.6
```

### Invariant 3: Stress Gate Availability (Explicitly Partial)
```
Given: Quintet codebase
When: Checking for pre-promotion stress gate mechanism
Then:
  - CLI script run_pre_promote.py exists at quintet/stress/run_pre_promote.py
  - Script can be invoked via subprocess
  - **Does NOT yet have importable Python API** (this is explicit, not hidden)
Result: WARN (not fully satisfied) because no programmatic API; FAIL if script missing entirely
Phase 2+ may change: PASS only if importable API exists
```

### Invariant 4: Receipt Chain & Persistence
```
Given: A PolicyExperiment + PolicyIntervention construction
When: Creating PolicyChangeReceipt and persisting via ReceiptStore
Then:
  - PolicyChangeReceipt.from_experiment() succeeds
  - compute_receipt_hash(receipt) returns stable 64-char hex string
  - ReceiptStore.append_receipt(receipt) writes to JSONL
  - ReceiptStore.read_all_receipts() reloads the receipt
  - Hash recomputed from reloaded receipt == original hash
Result: PASS if hash is stable across save/load; FAIL if persistence or hash diverges
```

---

## Core Types

### `ValidationCheckResult`

```python
@dataclass
class ValidationCheckResult:
    name: str                       # Check identifier
    passed: bool                    # Overall pass/fail
    warnings: List[str]             # Non-fatal issues
    errors: List[str]               # Fatal issues
    details: Dict[str, Any]         # Arbitrary metadata
```

**Every check returns one of these.** No implicit state; all judgment logic is explicit.

### `ValidationSummary`

```python
@dataclass
class ValidationSummary:
    checks: List[ValidationCheckResult]

    # Properties provide aggregated views:
    @property
    def passed_checks(self) -> int: ...
    @property
    def failures(self) -> List[str]: ...
    @property
    def all_passed(self) -> bool: ...
```

---

## Phase 1 Invariants

### 1. `check_episode_quality(episodes) → ValidationCheckResult`

**Invariant**: Episode export is structurally sane.

**Checks**:
- At least 1 episode present
- Episodes can be parsed as `LoomEpisode` objects
- No missing required fields (mode, outcome)

**Why it matters**: Ensures Loom's episode schema matches Quintet's expectations.

### 2. `check_recommendations(episodes) → ValidationCheckResult`

**Invariant**: Quintet analysis produces coherent recommendations.

**Checks**:
- Analysis pipeline runs without throwing
- Average confidence >= 0.6
- No internal analyzer errors

**Returns in details**:
- Per-lever recommendations (action, confidence)
- Average quality score

**Why it matters**: Validates that the core algorithm works on real data.

### 3. `check_stress_gates() → ValidationCheckResult`

**Invariant**: Pre-promotion safety checks are available.

**Current state (Phase 1.1)**:
- CLI script exists: ✅
- Importable Python API: ❌ (explicit, not hidden)

**Returns in details**:
- `mode`: "cli_only" or "missing"
- `warnings`: "available only via CLI"

**Why it matters**: Safety cannot be silent. We explicitly record "not yet programmatic" so Phase 2 can tighten requirements.

### 4. `check_receipt_chain(store_root=None) → ValidationCheckResult`

**Invariant**: Policy change receipts can be constructed, hashed, and persisted.

**Checks**:
1. Construct `PolicyIntervention` + `PolicyExperiment` + `PolicyChangeReceipt`
2. Compute SHA256 hash via `compute_receipt_hash()`
3. Persist to `ReceiptStore` (JSONL append-only)
4. Reload from store and recompute hash
5. Verify hash is stable across save/load

**Returns in details**:
- Receipt ID
- Hash prefix (first 16 chars)
- Persistence success

**Why it matters**: Audit trail must be immutable and verifiable. This isn't just "can we construct an object"; it's "can we actually persist and recover it."

---

## Usage

### As a CLI

```bash
# Run Phase 1 validation (uses default fixture)
python3 scripts/validate_phase_1_cli.py

# Or pass explicit fixture
python3 scripts/validate_phase_1_cli.py custom_episodes.json

# Exit code: 0 (passed), 1 (failed)
```

### As a Library

```python
from quintet.validation.phase1 import run_phase1_validation, summarize_phase1
from pathlib import Path
import json

# Load your episodes
data = json.loads(Path("episodes.json").read_text())
episodes = data["episodes"]

# Run validation
summary = run_phase1_validation(episodes)

# Inspect results programmatically
for check in summary.checks:
    if check.passed:
        print(f"✅ {check.name}")
    else:
        print(f"❌ {check.name}: {check.errors}")

# Get human-readable summary
result = summarize_phase1(summary)
if result["overall_pass"]:
    print("Phase 1 PASSED")
else:
    print(f"Phase 1 FAILED: {result['failures']}")
```

### In Tests

```python
import pytest
from quintet.validation.phase1 import check_episode_quality

def test_episode_schema():
    """Test that our fixtures have the right schema."""
    episodes = load_fixtures()
    result = check_episode_quality(episodes)
    assert result.passed, result.errors
```

### In Automated Systems

```python
from quintet.validation.phase1 import run_phase1_validation

def decide_whether_to_run_phase2(episodes):
    summary = run_phase1_validation(episodes)
    if summary.all_passed:
        return "proceed_to_phase2"
    elif summary.passed_checks >= 3 and not summary.failures:
        return "proceed_with_warnings"
    else:
        return "block_until_fixed"
```

---

## Design Principles

### 1. Invariants are Named Functions

Each check is a pure function:
```python
def check_X(...) -> ValidationCheckResult:
    # No side effects
    # No printing
    # Returns structured result
```

**Why**: Composable, testable, reusable.

### 2. Results are Structured, Not Textual

Instead of:
```python
print("Episode quality: PASS")
```

We have:
```python
ValidationCheckResult(
    name="episode_quality",
    passed=True,
    warnings=[],
    errors=[],
    details={"episode_count": 15, ...},
)
```

**Why**: Machines can parse and act on results. Humans can format them however they want.

### 3. Judgment Sits in the CLI, Not in Library

The library says:
> "Here are 4 checks. 3 passed, 1 warned."

The CLI says:
> "That means Phase 1 PASSED because we have >= 3 passes and no hard failures."

**Why**: Library is reusable across different policies. CLI reflects *your* decision logic.

### 4. Stress Gates are Explicit State, Not Silent Behavior

Phase 1.1 approach:

```python
# Stress gates check says:
ValidationCheckResult(
    name="stress_gates",
    passed=False,  # invariant not satisfied
    warnings=["CLI-only, no importable API"],
    errors=[],
)

# Phase 1 summary says:
"3/4 checks passed, 1 warning → Phase 1 PASSED"
```

Phase 2 can change the decision logic to:
```python
if result["failures"]:
    # Phase 2 requires ALL checks to pass
    block()
```

**Why**: Safety gates can't be hidden in heuristics. They must be visible, named, and subject to explicit judgment.

---

## Extending to Phase 2 & 3

Once Phase 1.1 is proven, Phase 2 follows the same pattern:

```
quintet/validation/phase2.py
├── check_loom_daemon_integration()
├── check_policy_application()
├── check_outcome_prediction()
├── run_phase2_validation()
└── summarize_phase2()

scripts/validate_phase_2_cli.py
```

Reuse `ValidationCheckResult`, `ValidationSummary`, and the CLI pattern.

---

## Testing the Validation System

Since invariants are pure functions, they're easy to test:

```python
import pytest
from quintet.validation.phase1 import check_episode_quality

def test_check_episode_quality_empty():
    """Empty episode list should fail."""
    result = check_episode_quality([])
    assert not result.passed
    assert "No episodes found" in result.errors[0]

def test_check_episode_quality_valid():
    """Valid episodes should pass."""
    episodes = load_valid_fixtures()
    result = check_episode_quality(episodes)
    assert result.passed
    assert len(result.errors) == 0
```

---

## Files Summary

| File | Purpose | Stability |
|------|---------|-----------|
| `quintet/validation/types.py` | Shared types | Stable (reused in Phase 2+) |
| `quintet/validation/phase1.py` | Invariant functions | Stable (frozen for Phase 1) |
| `quintet/validation/__init__.py` | Public API | Stable |
| `scripts/validate_phase_1_cli.py` | CLI entry point | Stable |
| `scripts/validate_phase_1.py` | Legacy wrapper | Stable (backward compat) |

---

## What Changed from Old Monolithic Script

| Old | New | Benefit |
|-----|-----|---------|
| Monolithic `validate_phase_1.py` | Library + CLI | Reusable, testable, composable |
| Mixed IO + logic | Pure functions | No side effects |
| Implicit error handling | Explicit errors in result | Clear judgment logic |
| Hardcoded pass/fail logic | Configurable via CLI | Easy to adjust criteria |
| Console output only | Structured data | Programmatic consumption |
| "Stress gates: skipped" (silent heuristic) | Explicit warning in result | Safety gates are visible |

---

## Exit Codes

```
0 = Phase 1 PASSED
1 = Phase 1 FAILED
```

---

## Next Steps

1. **Phase 2**: Create `quintet/validation/phase2.py` with same structure
2. **Integration**: Use `run_phase1_validation()` in CI/CD
3. **Automation**: Build decision logic that consumes `ValidationSummary`
4. **Receipt**: Create `Phase1ValidationReceipt` that mints a permanent record

---

**Created**: 2025-12-09
**Architecture**: Receipt-aligned, composable, no model branding
