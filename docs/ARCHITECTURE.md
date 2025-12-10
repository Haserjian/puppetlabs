# Quintet Architecture & Implementation Status

**Version**: `quintet-ultra-math-v1.2`  
**Last Updated**: December 9, 2024  
**Status**: Tier 1 Math Mode + Constitutional Enforcement + Robustness Complete  
**Tests**: ~60 across 3 suites (requires `pip install -e ".[math,dev]"` to run)

---

## Table of Contents

1. [System Overview](#system-overview)
2. [Architecture Diagram](#architecture-diagram)
3. [Core Modules](#core-modules)
4. [Implementation Status](#implementation-status)
5. [Key Contracts](#key-contracts)
6. [Constitutional Enforcement](#constitutional-enforcement)
7. [Data Flow](#data-flow)
8. [Testing](#testing)
9. [Pending Work](#pending-work)

---

## System Overview

Quintet is a multi-agent reasoning system designed for building and mathematical problem-solving with strong verification guarantees.

### Design Principles

| Principle | Implementation |
|-----------|----------------|
| **Single Source of Truth** | All shared types in `quintet/core/types.py` |
| **Verification First** | Multi-path validation before declaring success |
| **Constitutional Safety** | Runtime invariant enforcement with blocking |
| **Traceability** | Every decision logged to `context_flow` with receipts |
| **Graceful Degradation** | Optional backends fail gracefully, core always works |

### Component Hierarchy

```
┌─────────────────────────────────────────────────────────────┐
│                    QUINTET COUNCIL                          │
│          (5-agent deliberation: α β γ δ ε)                  │
│   IntentEnvelope → QuintetSynthesis → Treaty (if needed)    │
└────────────────────────┬────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────┐
│              CONSTITUTIONAL ENFORCER                         │
│    Pre-conditions (treaty?) → Execute → Post-conditions      │
│         CRITICAL blocks │ HIGH warns │ others log           │
└────────────────────────┬────────────────────────────────────┘
                         │
         ┌───────────────┴───────────────┐
         ▼                               ▼
┌─────────────────────┐       ┌─────────────────────┐
│    BUILD MODE       │       │    MATH MODE        │
│  (Ultra Mode 2.0)   │       │   (Math Mode 3.0)   │
│                     │       │                     │
│ Detector            │       │ Detector            │
│ SpecGenerator       │       │ Parser              │
│ Executor            │       │ Planner             │
│ Validator           │       │ Executor            │
│                     │       │ Validator           │
│                     │       │ Explainer           │
└─────────────────────┘       └─────────────────────┘
         │                               │
         └───────────────┬───────────────┘
                         ▼
┌─────────────────────────────────────────────────────────────┐
│                      BACKENDS                                │
│   SymPy (symbolic) │ NumPy/SciPy (numeric) │ Future: Lean   │
└─────────────────────────────────────────────────────────────┘
```

---

## Architecture Diagram

### Directory Structure

```
puppetlabs/
├── docs/
│   ├── QUINTET_ULTRA_MODE_REPLICATOR.md   # Full spec (176K)
│   └── ARCHITECTURE.md                     # This file
├── quintet/
│   ├── __init__.py
│   ├── core/                               # SHARED FOUNDATION
│   │   ├── __init__.py
│   │   ├── types.py           (491 lines) # Single source of truth
│   │   ├── router.py          (329 lines) # Mode arbitration
│   │   ├── council.py         (521 lines) # Intent, Synthesis, Treaty
│   │   └── constitutional.py  (883 lines) # Invariants + Enforcer
│   │
│   ├── builder/                            # BUILD MODE (Tier 0)
│   │   ├── __init__.py
│   │   ├── types.py           # BuildIntent, ProjectBlueprint, BuildResult
│   │   ├── detector.py        # Detect build requests
│   │   ├── specification.py   # Generate blueprints
│   │   ├── executor.py        # Execute blueprints
│   │   ├── ultra_mode.py      (767 lines) # OODA orchestrator
│   │   └── api.py             # FastAPI HTTP endpoints
│   │
│   ├── math/                               # MATH MODE (Tier 1)
│   │   ├── __init__.py
│   │   ├── types.py           # MathIntent, MathProblem, MathResult
│   │   ├── detector.py        # Detect math problems
│   │   ├── parser.py          # Parse to MathProblem
│   │   ├── planner.py         # Generate solution DAG
│   │   ├── executor.py        # Execute subgoals
│   │   ├── validator.py       # Multi-path verification
│   │   ├── math_mode.py       # OODA orchestrator
│   │   ├── robustness.py      # Capability matrix, normalizer, tolerance
│   │   └── backends/
│   │       ├── base.py        # MathBackend ABC
│   │       ├── sympy_backend.py   # Symbolic (SymPy)
│   │       └── numeric_backend.py # Numerical (NumPy/SciPy)
│   │
│   └── model/                              # LLM FABRIC (NEW)
│       ├── __init__.py
│       ├── types.py           # Message, ModelRequest, ModelResponse
│       ├── config.py          # ModelSlotConfig, ModelConfig
│       ├── router.py          # ModelRouter, ModelCallReceipt
│       ├── backends.py        # EchoBackend, OllamaBackend, OpenAI
│       ├── policy.py          # Call policies (temp caps, role gates)
│       └── factory.py         # Router factory functions
│
├── config/
│   └── model_slots.yaml       # Slot → provider/model mappings
│
├── tests/
│   ├── test_math_tier1.py              (22 tests)
│   ├── test_constitutional_enforcement.py (20 tests)
│   ├── test_robustness.py              (20 tests)
│   ├── test_model_fabric.py            (25+ tests) # NEW
│   └── fixtures/
│       └── high_stakes_healthcare.json
│
├── pyproject.toml             # Package definition
├── requirements.txt           # Dependencies
├── README.md                  # Quick start guide
└── .gitignore
```

---

## Core Modules

### `quintet/core/types.py` — Single Source of Truth

All shared types live here. Neither Build nor Math mode redefines them.

| Type | Purpose |
|------|---------|
| `ErrorCode` | Canonical error taxonomy (PARSE_ERROR, TIMEOUT, etc.) |
| `ModeError` | Structured error with stage, recoverable flag, action |
| `ValidationCheck` | Single validation check result |
| `ValidationResult` | Complete validation with confidence, diversity score |
| `ContextFlowEntry` | Single entry in decision audit trail |
| `CognitionSummary` | 3-sentence summary (observed, oriented, acted) |
| `IncompletenessAssessment` | Score + missing elements + next steps |
| `WorldImpactAssessment` | Category, impact score, verification tier |
| `ColorTile` / `ColorTileGrid` | 3x3 visual diagnostic grid |
| `ModeResultBase` | Base class for all mode results |
| `Mode` | Protocol that Build/Math modes implement |
| `ResourceLimits` | Per-tier compute budgets |
| `Receipt` | Base receipt for organism relay |

### `quintet/core/council.py` — Council Contracts

| Type | Purpose |
|------|---------|
| `IntentEnvelope` | Structured user intent with constraints |
| `QuintetSynthesis` | Council decision with agent votes |
| `Treaty` | Formal agreement for high-stakes flows |
| `AgentRole` / `AgentVote` | 5-agent council (α β γ δ ε) |
| `ArbitrationPolicy` | When council runs vs router bypasses |
| `SessionContext` | Multi-turn state across modes |
| `CouncilDecisionReceipt` | Audit trail for council decisions |

### `quintet/core/constitutional.py` — Runtime Enforcement

| Type | Purpose |
|------|---------|
| `ConstitutionalInvariant` | Safety law with precedence + predicate |
| `ConstitutionalEnforcer` | Runtime pre/post condition checker |
| `EnforcementResult` | Check result with allowed/blocked status |
| `ConstitutionalBlockReceipt` | Receipt when action blocked |
| `ConstitutionalViolationReceipt` | Receipt when violation detected |
| `ConstitutionalPassReceipt` | Audit trail when checks pass |

### `quintet/core/router.py` — Mode Arbitration

```python
class UltraModeRouter:
    """Routes queries to appropriate mode based on intent detection."""
    
    # Thresholds
    MATH_STRONG_THRESHOLD = 0.75
    MATH_WEAK_THRESHOLD = 0.5
    BUILD_STRONG_THRESHOLD = 0.7
    BUILD_WEAK_THRESHOLD = 0.4
```

---

## Implementation Status

### Tier 0: Core + Build Mode ✅

| Component | Status | Notes |
|-----------|--------|-------|
| `core/types.py` | ✅ Complete | Single source of truth |
| `core/router.py` | ✅ Complete | Mode arbitration |
| `core/council.py` | ✅ Complete | Intent, Synthesis, Treaty |
| `core/constitutional.py` | ✅ Complete | Runtime enforcement |
| `builder/detector.py` | ✅ Complete | Build intent detection |
| `builder/specification.py` | ✅ Complete | Blueprint generation |
| `builder/executor.py` | ✅ Complete | File/command execution |
| `builder/ultra_mode.py` | ✅ Complete | OODA orchestrator |
| `builder/api.py` | ✅ Complete | FastAPI endpoints |

### Tier 1: Math Mode Core ✅

| Component | Status | Notes |
|-----------|--------|-------|
| `math/detector.py` | ✅ Complete | Math intent detection |
| `math/parser.py` | ✅ Complete | Problem parsing |
| `math/planner.py` | ✅ Complete | Subgoal DAG generation |
| `math/executor.py` | ✅ Complete | Plan execution |
| `math/validator.py` | ✅ Complete | Multi-path verification |
| `math/explainer.py` | ✅ Complete | Step-by-step explanations |
| `math/math_mode.py` | ✅ Complete | OODA orchestrator |
| `backends/sympy_backend.py` | ✅ Complete | Symbolic math |
| `backends/numeric_backend.py` | ✅ Complete | Numerical math |
| `math/robustness.py` | ✅ Complete | Hardening utilities |

### Robustness Utilities (`quintet/math/robustness.py`) ✅ NEW

Hardening utilities for multivariate math and production reliability:

| Utility | Purpose |
|---------|---------|
| **Capability Matrix** | Register/check backend capabilities before planning |
| **Solution Normalizer** | Canonicalize SymPy outputs (dict/list/tuple → consistent shape) |
| **Canonical Variable Order** | Stable ordering for gradients/Hessians (prevents misalignment) |
| **Tolerance-Based Verification** | Handle floating-point issues in substitution checks |
| **Finite-Difference Gradient Check** | Cross-check symbolic derivatives numerically |
| **Complexity Estimation** | Route large systems to numeric-first path |

#### Capability Registration

```python
from quintet.math.robustness import MathCapability, check_capability

# Before planning a solve:
available, reason = check_capability("sympy", MathCapability.SOLVE_SYSTEM)
if not available:
    # Return error subgoal instead of runtime failure
```

#### Solution Normalization

```python
from quintet.math.robustness import normalize_sympy_solution

# SymPy returns various shapes; normalize to consistent form
raw = sympy.solve([eq1, eq2], [x, y])
normalized = normalize_sympy_solution(raw, ["x", "y"])

# Always access via:
for sol in normalized.solutions:
    print(sol["x"], sol["y"])
print(normalized.variable_order)  # Canonical ordering
```

#### Tolerance-Based Checks

```python
from quintet.math.robustness import substitution_check_with_tolerance

# Handles floating-point residuals gracefully
passed, residual, msg = substitution_check_with_tolerance(
    "x**2 - 4",
    {"x": 2.0000000001}  # Near-exact solution
)
# passed=True, residual≈1e-9
```

### Tier 2: Advanced (Optional) ⏳

| Component | Status | Notes |
|-----------|--------|-------|
| CVXPY backend | ⏳ Not started | Optimization |
| statsmodels backend | ⏳ Not started | Statistics |
| PyTorch/JAX backend | ⏳ Not started | ML |
| FEniCS backend | ⏳ Not started | PDEs |
| Lean backend | ⏳ Not started | Formal proofs |
| Wolfram backend | ⏳ Not started | External API |
| Proof Atlas | ⏳ Not started | Strategy memory |

---

## Key Contracts

### ModeResultBase

Every mode result inherits/composes these fields:

```python
@dataclass
class ModeResultBase:
    result_id: str              # Unique ID
    spec_version: str           # "quintet-ultra-math-v1.2"
    mode: str                   # "build" | "math"
    success: bool               # Overall success
    errors: List[ModeError]     # Structured errors
    context_flow: List[ContextFlowEntry]  # Decision trail
    color_tiles: ColorTileGrid  # Visual diagnostics
    cognition_summary: CognitionSummary   # 3-sentence summary
    incompleteness: IncompletenessAssessment
    world_impact: WorldImpactAssessment
    total_time_ms: float
```

### ValidationResult

```python
@dataclass
class ValidationResult:
    valid: bool
    confidence: float           # 0.0-1.0
    checks: List[ValidationCheck]
    warnings: List[str]
    suggested_review: bool
    
    @property
    def diversity_score(self) -> float:
        """How diverse were verification methods? High = stronger trust."""
```

### IntentEnvelope → QuintetSynthesis

```python
# User intent structured by council
IntentEnvelope:
    raw_query: str
    goal: str
    constraints: List[str]
    invariants: List[str]       # Must never be violated
    risk_level: "low" | "medium" | "high" | "critical"
    world_impact_category: Optional[str]

# Council decision
QuintetSynthesis:
    intent: IntentEnvelope
    decision: "proceed" | "reject" | "defer" | "escalate"
    votes: List[AgentVote]      # 5 agents
    dissent: bool
    guardrails: List[str]
    treaty: Optional[Treaty]    # Required for high-stakes
```

---

## Constitutional Enforcement

### How It Works

```
                     ┌────────────────────┐
                     │   User Request     │
                     └─────────┬──────────┘
                               │
                               ▼
                     ┌────────────────────┐
                     │  PRE-CHECK         │
                     │  (Treaty exists?)  │
                     │  CRITICAL → Block  │
                     │  HIGH → Warn       │
                     └─────────┬──────────┘
                               │
                    ┌──────────┴──────────┐
                    │                     │
                    ▼ Blocked             ▼ Allowed
         ┌──────────────────┐   ┌──────────────────┐
         │ Return Error     │   │  EXECUTE         │
         │ + BlockReceipt   │   │  (Build/Math)    │
         └──────────────────┘   └─────────┬────────┘
                                          │
                                          ▼
                               ┌──────────────────┐
                               │  POST-CHECK      │
                               │  (Timestamps OK?)│
                               │  (Dignity OK?)   │
                               └─────────┬────────┘
                                         │
                              ┌──────────┴──────────┐
                              │                     │
                              ▼ Violation           ▼ Pass
                   ┌──────────────────┐   ┌──────────────────┐
                   │ Mark + Escalate  │   │ Return Success   │
                   │ + ViolationReceipt│  │ + PassReceipts   │
                   └──────────────────┘   └──────────────────┘
```

### Standard Invariants

| Name | Precedence | Severity | Phase | Description |
|------|------------|----------|-------|-------------|
| Dignity Floor | 90 | CRITICAL | POST | Dignity score ≥ 0.15 |
| Tri-Temporal | 80 | CRITICAL | POST | Timestamps ordered correctly |
| Treaty Compliance | 60 | CRITICAL | PRE | High-stakes needs treaty |
| Receipt Continuity | 50 | HIGH | POST | No gaps in receipt chain |

### Severity Behavior

| Severity | Normal Mode | Strict Mode |
|----------|-------------|-------------|
| CRITICAL | **Block** | **Block** |
| HIGH | Warn (continue) | **Block** |
| MEDIUM | Log | Log |
| LOW | Log | Log |

### Example: Blocked Action

```python
# High-stakes healthcare without treaty
synthesis = QuintetSynthesis(
    risk_level="critical",
    world_impact_category="healthcare_medicine",
    treaty=None  # No treaty!
)

result = math_mode.process("Calculate drug dosage", council_synthesis=synthesis)

# Result:
# - success: False
# - errors: [ModeError(code=WORLD_IMPACT_BLOCKED, ...)]
# - enforcement_receipts: [ConstitutionalBlockReceipt(...)]
```

---

## Data Flow

### Math Mode OODA Loop

```
OBSERVE                  ORIENT                   DECIDE                    ACT
   │                        │                        │                        │
   ▼                        ▼                        ▼                        ▼
┌─────────┐            ┌─────────┐            ┌─────────┐            ┌─────────┐
│ Detect  │────────────│ Parse   │────────────│ Plan    │────────────│ Execute │
│ Intent  │            │ Problem │            │ DAG     │            │ Steps   │
└─────────┘            └─────────┘            └─────────┘            └─────────┘
     │                      │                      │                      │
     │                      │                      │        ┌─────────────┤
     │                      │                      │        │             │
     │                      │                      │        ▼             ▼
     │                      │                      │   ┌─────────┐   ┌─────────┐
     │                      │                      │   │ Validate│   │ Explain │
     │                      │                      │   │ Result  │   │ Steps   │
     │                      │                      │   └─────────┘   └─────────┘
     │                      │                      │        │
     ▼                      ▼                      ▼        ▼
┌───────────────────────────────────────────────────────────────────────────────┐
│                              CONTEXT FLOW                                      │
│  [observe: query→intent] [orient: intent→problem] [decide: problem→plan] ...  │
└───────────────────────────────────────────────────────────────────────────────┘
```

### Build Mode OODA Loop

```
OBSERVE                  ORIENT                   DECIDE                    ACT
   │                        │                        │                        │
   ▼                        ▼                        ▼                        ▼
┌─────────┐            ┌─────────┐            ┌─────────┐            ┌─────────┐
│ Detect  │────────────│ Scan    │────────────│ Generate│────────────│ Execute │
│ Intent  │            │ Context │            │ Blueprint            │ Files   │
└─────────┘            └─────────┘            └─────────┘            └─────────┘
                                                   │                      │
                                    Optional       │                      │
                                    ┌──────────────┤                      │
                                    ▼              │                      ▼
                              ┌─────────┐          │               ┌─────────┐
                              │ Approval│          │               │ Validate│
                              │ Hook    │          │               │ Output  │
                              └─────────┘          │               └─────────┘
                                                   │
                            CONSTITUTIONAL         │
                            PRE-CHECK ─────────────┘
```

---

## Testing

### Test Suites

```bash
# Run all tests
pytest tests/ -v

# Run specific suites
pytest tests/test_math_tier1.py -v              # 20 tests
pytest tests/test_constitutional_enforcement.py -v  # 20 tests
```

### Coverage Summary

| Suite | Tests | Status |
|-------|-------|--------|
| Math Detector | 4 | ✅ Pass |
| Problem Parser | 2 | ✅ Pass |
| SymPy Backend | 4 | ✅ Pass |
| Numeric Backend | 2 | ✅ Pass |
| Math Orchestrator | 5 | ✅ Pass |
| Core Types | 3 | ✅ Pass |
| Invariant Precedence | 4 | ✅ Pass |
| Pre-condition Checks | 4 | ✅ Pass |
| Post-condition Checks | 3 | ✅ Pass |
| Strict Mode | 2 | ✅ Pass |
| Enforcement Receipts | 3 | ✅ Pass |
| Integration | 4 | ✅ Pass |
| **Total** | **40** | ✅ **All Pass** |

---

## Pending Work

### Near-term (Recommended Next Steps)

| Task | Priority | Complexity |
|------|----------|------------|
| Expand math domain coverage (multi-variable) | Medium | Medium |
| Add end-to-end build tests | Medium | Low |
| Implement council deliberation logic | High | High |
| Add router + council integration | High | Medium |
| Human oversight pause points | Medium | Low |

### Tier 2 (Future)

| Task | Notes |
|------|-------|
| Optimization backend (CVXPY) | Convex optimization |
| Statistics backend (statsmodels) | Regression, hypothesis testing |
| ML backend (PyTorch/JAX) | Neural networks |
| PDE backend (FEniCS) | Partial differential equations |
| Formal backend (Lean) | Theorem proving |
| Proof Atlas | Strategy memory + retrieval |

### Infrastructure

| Task | Notes |
|------|-------|
| CI/CD pipeline | GitHub Actions with pytest |
| Docker container | Reproducible environment |
| API documentation | OpenAPI/Swagger |
| Performance benchmarks | Track solver times |

---

## Quick Reference

### Running the System

```python
from quintet.math.math_mode import MathModeOrchestrator
from quintet.builder.ultra_mode import UltraModeOrchestrator
from quintet.core.council import IntentEnvelope, QuintetSynthesis, Treaty

# Math Mode
math = MathModeOrchestrator()
result = math.process("Solve x^2 - 4 = 0")
print(result.result.final_answer)  # [-2, 2]

# Build Mode
build = UltraModeOrchestrator(project_root="/path/to/project")
result = build.process("Create a utils.py file")

# High-stakes with treaty
treaty = Treaty(name="Medical", domains=["healthcare_medicine"], status="active")
synthesis = QuintetSynthesis(
    risk_level="critical",
    world_impact_category="healthcare_medicine",
    treaty=treaty
)
result = math.process("Calculate dosage", council_synthesis=synthesis)
```

### Key Imports

```python
# Core types
from quintet.core.types import (
    ModeResultBase, ValidationResult, ContextFlowEntry,
    CognitionSummary, IncompletenessAssessment, WorldImpactAssessment,
    ColorTileGrid, ErrorCode, ModeError
)

# Council
from quintet.core.council import (
    IntentEnvelope, QuintetSynthesis, Treaty, AgentRole, AgentVote
)

# Constitutional
from quintet.core.constitutional import (
    ConstitutionalEnforcer, ConstitutionalInvariant,
    STANDARD_INVARIANTS, InvariantSeverity, CheckPhase
)

# Modes
from quintet.math.math_mode import MathModeOrchestrator
from quintet.builder.ultra_mode import UltraModeOrchestrator
```

---

*This document is auto-generated and should be kept in sync with the codebase.*

