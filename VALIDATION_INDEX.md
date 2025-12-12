# Validation System: Complete Index

**Status**: ✅ Phase 1 & 2 Complete, Ready for Production
**Date**: 2025-12-10
**Latest**: Phase 2 Implementation Complete

---

## Quick Start

**First Time?** → Start here: [`START_HERE.md`](./START_HERE.md)

**Want to run Phase 1?** → `python3 scripts/validate_phase_1_cli.py`

**Want to run Phase 2?** → `python3 scripts/validate_phase_2_cli.py --loom-url http://localhost:8000 --quintet-url http://localhost:9000`

---

## Documentation Index

### Entry Points (Read These First)

| Document | Purpose | Read When |
|----------|---------|-----------|
| **[START_HERE.md](./START_HERE.md)** | Ultimate entry point | You're new to the system |
| **[VALIDATION_COMPLETE_V2.md](./VALIDATION_COMPLETE_V2.md)** | Complete system overview (Phase 1 & 2) | You want the big picture |
| **[VALIDATION_README.md](./VALIDATION_README.md)** | Quick start guide | You want a fast introduction |

### Phase 1 Documentation

| Document | Purpose | Read When |
|----------|---------|-----------|
| **[VALIDATION_SYSTEM_COMPLETE.md](./VALIDATION_SYSTEM_COMPLETE.md)** | Gold standard checklist for Phase 1 | You want phase 1 details |
| **[PHASE_1_REPORT.md](./PHASE_1_REPORT.md)** | Phase 1 detailed results | You want to see Phase 1 results |
| **[VALIDATION_ARCHITECTURE.md](./VALIDATION_ARCHITECTURE.md)** | Formal invariants + system design | You want the "physics" |

### Phase 2 Documentation

| Document | Purpose | Read When |
|----------|---------|-----------|
| **[PHASE_2_IMPLEMENTATION_GUIDE.md](./PHASE_2_IMPLEMENTATION_GUIDE.md)** | How to run Phase 2 + troubleshooting | You're deploying Phase 2 |
| **[PHASE_2_STATUS.md](./PHASE_2_STATUS.md)** | Implementation details + design decisions | You want implementation details |
| **[PHASE_2_BLUEPRINT.md](./PHASE_2_BLUEPRINT.md)** | Original Phase 2 specification | You want the original spec |
| **[PHASE_2_COMPLETE_SUMMARY.txt](./PHASE_2_COMPLETE_SUMMARY.txt)** | Executive summary | You want a concise overview |

### Reference Documents

| Document | Purpose | Read When |
|----------|---------|-----------|
| **[VALIDATION_COMPLETE_SUMMARY.txt](./VALIDATION_COMPLETE_SUMMARY.txt)** | Metrics & status (older) | You want metrics |
| **[PHASE_1_1_REFACTOR_SUMMARY.md](./PHASE_1_1_REFACTOR_SUMMARY.md)** | How Phase 1.1 refactoring happened | You want the story |
| **[VALIDATION_STATUS.md](./VALIDATION_STATUS.md)** | Phase 1-4 status dashboard | You want high-level status |

---

## Code Index

### Core Library Files

| File | Lines | Purpose |
|------|-------|---------|
| **[quintet/validation/types.py](./quintet/validation/types.py)** | 130 | ValidationCheckResult, ValidationSummary (reusable) |
| **[quintet/validation/phase1.py](./quintet/validation/phase1.py)** | 380 | Phase 1: 4 invariant checks (test data) |
| **[quintet/validation/phase2.py](./quintet/validation/phase2.py)** | 400 | Phase 2: 3 invariant checks (live system) |
| **[quintet/validation/__init__.py](./quintet/validation/__init__.py)** | 50 | Public API exports |
| **[quintet/causal/validation_receipts.py](./quintet/causal/validation_receipts.py)** | 220 | Receipt types (Phase 1/2/3) |

### CLI Entry Points

| File | Lines | Purpose |
|------|-------|---------|
| **[scripts/validate_phase_1_cli.py](./scripts/validate_phase_1_cli.py)** | 150 | Phase 1 CLI with receipt minting |
| **[scripts/validate_phase_2_cli.py](./scripts/validate_phase_2_cli.py)** | 150 | Phase 2 CLI with receipt minting |
| **[scripts/validate_phase_1.py](./scripts/validate_phase_1.py)** | 40 | Phase 1 legacy wrapper |

### Test Fixtures

| File | Lines | Purpose |
|------|-------|---------|
| **[tests/fixtures/loom_export_sample.json](./tests/fixtures/loom_export_sample.json)** | 150 | 15 synthetic episodes for Phase 1 |
| **[tests/fixtures/phase2_test_episodes.py](./tests/fixtures/phase2_test_episodes.py)** | 100 | Episode definitions for Phase 2 |

---

## Cheat Sheet

### Running Validation

```bash
# Phase 1 (test data)
python3 scripts/validate_phase_1_cli.py

# Phase 2 (live system) - requires Loom + Quintet running
python3 scripts/validate_phase_2_cli.py \
    --loom-url http://localhost:8000 \
    --quintet-url http://localhost:9000

# With custom receipt storage
python3 scripts/validate_phase_2_cli.py \
    --store-root .my_receipts
```

### Querying Receipts

```python
from quintet.causal.receipt_persistence import ReceiptStore

# Phase 1 receipts
store = ReceiptStore(".quintet_validation_receipts/phase1_receipts.jsonl")
for receipt in store.read_all_receipts():
    print(f"{receipt.receipt.phase}: {receipt.receipt.passed}")

# Phase 2 receipts (after first run)
store = ReceiptStore(".quintet_validation_receipts/phase2_receipts.jsonl")
for receipt in store.read_all_receipts():
    print(f"{receipt.receipt.phase}: {receipt.receipt.passed}")
```

### Using Library Directly

```python
from quintet.validation import (
    run_phase1_validation, summarize_phase1,
    run_phase2_validation, summarize_phase2,
)
import json

# Phase 1
with open("tests/fixtures/loom_export_sample.json") as f:
    episodes = json.load(f)
summary = run_phase1_validation(episodes)
result = summarize_phase1(summary)
print(f"Phase 1: {'PASS' if result['overall_pass'] else 'FAIL'}")

# Phase 2
summary = run_phase2_validation(
    loom_daemon_url="http://localhost:8000",
    quintet_service_url="http://localhost:9000",
)
result = summarize_phase2(summary)
print(f"Phase 2: {'PASS' if result['overall_pass'] else 'FAIL'}")
```

---

## Workflow

### Typical First-Time User

1. Read [`START_HERE.md`](./START_HERE.md) (5 min)
2. Read [`VALIDATION_COMPLETE_V2.md`](./VALIDATION_COMPLETE_V2.md) (10 min)
3. Run Phase 1: `python3 scripts/validate_phase_1_cli.py` (2 sec)
4. Review receipt: `cat .quintet_validation_receipts/phase1_receipts.jsonl | python3 -m json.tool` (1 min)
5. Read [`PHASE_2_IMPLEMENTATION_GUIDE.md`](./PHASE_2_IMPLEMENTATION_GUIDE.md) (15 min)
6. Deploy Phase 2 on your live system (time varies)
7. Run Phase 2: `python3 scripts/validate_phase_2_cli.py` (30-60 sec)
8. Document results in `PHASE_2_REPORT.md`

### Troubleshooting

1. **Phase 1 fails?** → See `VALIDATION_ARCHITECTURE.md` section "Phase 1 Results"
2. **Phase 2 fails?** → See `PHASE_2_IMPLEMENTATION_GUIDE.md` section "Troubleshooting"
3. **Receipt issues?** → See `VALIDATION_ARCHITECTURE.md` section "Receipt Internet"
4. **Integration questions?** → See `PHASE_2_IMPLEMENTATION_GUIDE.md` section "Integrating with Your Systems"

---

## Architecture Overview

```
Formal Invariants (explicit physics)
        ↓
Pure Functions (no side effects)
        ↓
ValidationCheckResult (structured)
        ↓
ValidationSummary (aggregated)
        ↓
ValidationReceipt (first-class, auditable)
        ↓
ReceiptStore (JSONL, hash chain, persisted)
```

Same pattern for Phase 1, 2, 3, 4.

---

## Key Concepts

### Invariants

Formal statements of what must be true:
- **Given**: Precondition
- **When**: Action taken
- **Then**: Expected outcome
- **Result**: Success criterion

Example: "**Invariant 1**: Episode Export Structure - Given 15 episodes, When loading, Then all have required fields, Result: PASS if all parse"

### ValidationCheckResult

Atomic unit of validation:
- `name`: Check identifier
- `passed`: True/False
- `warnings`: Non-critical issues
- `errors`: Critical issues
- `details`: Context data

### ValidationSummary

Aggregation of multiple checks:
- `checks`: List of ValidationCheckResult
- Properties: `.passed_checks`, `.failures`, `.all_passed`

### ValidationReceipt

Proof of validation:
- `receipt_id`: UUID
- `timestamp`: When validation ran
- `phase`: "phase1" | "phase2" | "phase3" | "phase4"
- `passed`: Overall result
- `checks`: Dict of check results
- `receipt_hash`: SHA256 for integrity

---

## FAQ

**Q: Can I run Phase 2 without Phase 1?**
A: Yes, they're independent. Phase 1 is a prerequisite conceptually (proves test data works) but technically separate.

**Q: How do I add a new phase?**
A: Follow the pattern:
1. Create `quintet/validation/phaseN.py` with check functions
2. Create `scripts/validate_phaseN_cli.py` (mirror Phase 1/2)
3. Add `PhaseNValidationReceipt` to `validation_receipts.py`
4. Export from `quintet/validation/__init__.py`
5. Document in `PHASE_N_BLUEPRINT.md` and `PHASE_N_IMPLEMENTATION_GUIDE.md`

**Q: How do I integrate with CI/CD?**
A: Both validation scripts return exit code 0 (PASS) or 1 (FAIL). Add to CI pipeline:
```yaml
- name: Phase 1 Validation
  run: python3 scripts/validate_phase_1_cli.py
- name: Phase 2 Validation
  run: python3 scripts/validate_phase_2_cli.py
```

**Q: How do I query receipts programmatically?**
A: Use ReceiptStore:
```python
from quintet.causal.receipt_persistence import ReceiptStore
store = ReceiptStore(".quintet_validation_receipts/phase1_receipts.jsonl")
receipts = store.read_all_receipts()
```

**Q: Can I run Phase 2 against production?**
A: No. Phase 2 uses test mode exclusively. It's designed for staging/test environments. For production validation, add Phase 3/4.

---

## File Structure

```
puppetlabs/
├── quintet/
│   ├── validation/
│   │   ├── __init__.py          # Public API
│   │   ├── types.py              # Core types (reusable)
│   │   ├── phase1.py             # Phase 1 checks
│   │   └── phase2.py             # Phase 2 checks
│   └── causal/
│       └── validation_receipts.py # Receipt types
├── scripts/
│   ├── validate_phase_1_cli.py   # Phase 1 CLI
│   ├── validate_phase_2_cli.py   # Phase 2 CLI
│   └── validate_phase_1.py       # Legacy wrapper
├── tests/
│   └── fixtures/
│       ├── loom_export_sample.json # Phase 1 data
│       └── phase2_test_episodes.py # Phase 2 data
├── .quintet_validation_receipts/
│   ├── phase1_receipts.jsonl     # Phase 1 receipts
│   └── phase2_receipts.jsonl     # Phase 2 receipts (after first run)
├── START_HERE.md                  # Entry point
├── VALIDATION_*.md               # Documentation (8 files)
├── PHASE_*.md                    # Phase-specific docs (4 files)
├── VALIDATION_INDEX.md           # This file
└── ... (other project files)
```

---

## Status Summary

| Component | Status | Ready? |
|-----------|--------|--------|
| Phase 1 Library | ✅ Complete | Yes, use now |
| Phase 1 CLI | ✅ Complete | Yes, use now |
| Phase 1 Receipts | ✅ Complete | Yes, use now |
| Phase 2 Library | ✅ Complete | Yes, use now |
| Phase 2 CLI | ✅ Complete | Yes, use now |
| Phase 2 Receipts | ✅ Complete | Yes, use now |
| Phase 2 Testing (live) | 🟡 Ready | Pending deployment |
| Phase 3 Blueprint | 🟡 Ready | After Phase 2 |
| Phase 4 Blueprint | 🟡 Ready | After Phase 3 |

---

## Contact / Support

- **How to run?** → [`PHASE_2_IMPLEMENTATION_GUIDE.md`](./PHASE_2_IMPLEMENTATION_GUIDE.md)
- **What's failing?** → [`PHASE_2_IMPLEMENTATION_GUIDE.md`](./PHASE_2_IMPLEMENTATION_GUIDE.md) → Troubleshooting
- **How does it work?** → [`VALIDATION_ARCHITECTURE.md`](./VALIDATION_ARCHITECTURE.md)
- **What's next?** → [`VALIDATION_COMPLETE_V2.md`](./VALIDATION_COMPLETE_V2.md) → Next Steps

---

## Key Links

| Type | Link |
|------|------|
| **Start** | [`START_HERE.md`](./START_HERE.md) |
| **Overview** | [`VALIDATION_COMPLETE_V2.md`](./VALIDATION_COMPLETE_V2.md) |
| **Run Phase 2** | [`PHASE_2_IMPLEMENTATION_GUIDE.md`](./PHASE_2_IMPLEMENTATION_GUIDE.md) |
| **Design** | [`VALIDATION_ARCHITECTURE.md`](./VALIDATION_ARCHITECTURE.md) |
| **Code** | `quintet/validation/` |
| **Receipts** | `.quintet_validation_receipts/` |

---

**Version**: 2.0 (Phase 1 + Phase 2 Complete)
**Date**: 2025-12-10
**Status**: 🟢 Production Ready

---

Start with [`START_HERE.md`](./START_HERE.md) or jump to the guide you need above.
