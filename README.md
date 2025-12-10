# Quintet

**Multi-Agent Orchestrator + Ultra Mode 2.0 + Math Mode 3.0**

Spec Version: `quintet-ultra-math-v1.2`  
Status: **Tier 1 Complete** (Math Mode + Constitutional Enforcement)

---

## Overview

Quintet is a multi-agent reasoning system with:

- **Quintet Council**: 5-agent deliberation (Alpha/Beta/Gamma/Delta/Epsilon)
- **Ultra Mode 2.0**: Context-aware builder with OODA loop, validation, rollback
- **Math Mode 3.0**: Research-grade math/stats/ML reasoning with verification
- **Constitutional Layer**: Runtime invariant enforcement, treaties, receipts

### Key Features

| Feature | Description |
|---------|-------------|
| **Constitutional Enforcement** | Pre/post condition checks block unsafe actions |
| **Treaty Compliance** | High-stakes domains require active treaties |
| **Multi-path Verification** | Symbolic + numerical validation |
| **Full Traceability** | Every decision logged to context_flow |

---

## Quick Start

```bash
# Clone and enter
cd puppetlabs

# Create virtual environment
python3 -m venv .venv
source .venv/bin/activate

# Install with Math Mode support
pip install -e ".[math,dev]"

# Run all tests (~60 tests across 3 suites)
pytest tests/ -v

# Try the Math Mode CLI
python -m quintet.cli "Solve x^2 - 4 = 0"

# Start Build API (optional)
pip install -e ".[api]"
uvicorn quintet.builder.api:app --host 127.0.0.1 --port 8000
# Or use the entry point:
quintet-api
```

---

## Architecture

```
quintet/
├── core/                   # SHARED FOUNDATION
│   ├── types.py            # Single source of truth (Episode, trust_score, etc.)
│   ├── router.py           # UltraModeRouter (mode arbitration)
│   ├── council.py          # IntentEnvelope, QuintetSynthesis, Treaty
│   └── constitutional.py   # Invariants + Runtime Enforcer
│
├── builder/                # BUILD MODE (Tier 0)
│   ├── detector.py         # Detect build requests
│   ├── specification.py    # Generate blueprints
│   ├── executor.py         # Execute blueprints
│   ├── ultra_mode.py       # OODA orchestrator
│   └── api.py              # HTTP API (exposes `app` for uvicorn)
│
├── math/                   # MATH MODE (Tier 1)
│   ├── detector.py         # Detect math problems
│   ├── parser.py           # Parse to MathProblem
│   ├── planner.py          # Generate solution DAG
│   ├── executor.py         # Execute subgoals
│   ├── validator.py        # Multi-path verification (tolerance-based)
│   ├── robustness.py       # Capability matrix, normalizer, tolerance
│   ├── math_mode.py        # OODA orchestrator
│   └── backends/           # SymPy, NumPy/SciPy
│
└── cli.py                  # Sandbox CLI (python -m quintet.cli)
```

📖 **Full architecture details**: [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md)

---

## Usage

### Math Mode

```python
from quintet.math.math_mode import MathModeOrchestrator

math = MathModeOrchestrator()
result = math.process("Solve x^2 - 4 = 0")

print(result.success)              # True
print(result.result.final_answer)  # [-2, 2]
print(result.validation.confidence)  # 0.8+
```

### Build Mode

```python
from quintet.builder.ultra_mode import UltraModeOrchestrator

build = UltraModeOrchestrator(project_root="/path/to/project")
result = build.process("Create a Python module for user authentication")

print(result.success)
print(result.blueprint.files)
```

### High-Stakes with Treaty (Constitutional Enforcement)

```python
from quintet.math.math_mode import MathModeOrchestrator
from quintet.core.council import IntentEnvelope, QuintetSynthesis, Treaty

# High-stakes healthcare WITHOUT treaty → BLOCKED
math = MathModeOrchestrator()
synthesis = QuintetSynthesis(
    risk_level="critical",
    world_impact_category="healthcare_medicine",
    treaty=None  # No treaty!
)
result = math.process("Calculate drug dosage", council_synthesis=synthesis)
print(result.success)  # False
print(result.errors[0].code)  # WORLD_IMPACT_BLOCKED

# With active treaty → ALLOWED
treaty = Treaty(
    name="Medical Calculation Treaty",
    domains=["healthcare_medicine"],
    status="active"
)
synthesis_with_treaty = QuintetSynthesis(
    risk_level="critical",
    world_impact_category="healthcare_medicine",
    treaty=treaty
)
result = math.process("Solve 5 * 70", council_synthesis=synthesis_with_treaty)
print(result.success)  # True
```

---

## Constitutional Invariants

The system enforces 4 standard invariants:

| Invariant | Severity | Phase | Description |
|-----------|----------|-------|-------------|
| **Dignity Floor** | CRITICAL | POST | Dignity score ≥ 0.15 |
| **Tri-Temporal** | CRITICAL | POST | Timestamps properly ordered |
| **Treaty Compliance** | CRITICAL | PRE | High-stakes requires treaty |
| **Receipt Continuity** | HIGH | POST | No gaps in receipt chain |

- **CRITICAL** violations → **Block action**
- **HIGH** violations → Warn (or block in strict mode)
- **MEDIUM/LOW** → Log only

---

## Testing

```bash
# Run all tests (~60 tests)
pytest tests/ -v

# Individual test suites
pytest tests/test_math_tier1.py -v               # 22 Math Mode tests
pytest tests/test_constitutional_enforcement.py -v  # 20 Constitutional tests
pytest tests/test_robustness.py -v               # 20 Robustness tests (conditional on deps)
```

**Note**: Tests require dependencies installed via `pip install -e ".[math,dev]"`

---

## Documentation

| Document | Description |
|----------|-------------|
| [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) | Implementation status, module overview, data flow |
| [docs/QUINTET_ULTRA_MODE_REPLICATOR.md](docs/QUINTET_ULTRA_MODE_REPLICATOR.md) | Full specification (176K) |

---

## Implementation Status

| Tier | Status | Components |
|------|--------|------------|
| **Tier 0** | ✅ Complete | Core types, Build Mode, HTTP API |
| **Tier 1** | ✅ Complete | Math Mode, SymPy/NumPy backends, Constitutional Enforcement |
| **Tier 2** | ⏳ Pending | CVXPY, statsmodels, PyTorch, Lean, Proof Atlas |

---

## License

MIT
