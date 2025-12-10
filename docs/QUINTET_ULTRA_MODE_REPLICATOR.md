# Quintet + Ultra Mode 2.0 Replicator

**Spec Version: `quintet-ultra-math-v1.1`**

> Build-spec for a **no-context AI** (or human) to reconstruct the Quintet multi-agent orchestrator + Ultra Mode 2.0 "nervous system" + Math Mode 3.0 on a fresh machine.

---

## Spec v1.1 Overview (Read This First)

### What Changed in v1.1

1. **Single Source of Truth**: All shared types now live in `quintet/core/types.py`. Build Mode and Math Mode **import** from there—no duplicates.

2. **Clear Implementation Tiers**:
   - **Tier 0 (Required)**: Core types, Build Mode, HTTP API
   - **Tier 1 (Required for Math)**: Math Mode with SymPy + NumPy/SciPy
   - **Tier 2 (Optional)**: Advanced packs (CVXPY, statsmodels, PyTorch, FEniCS, Lean, etc.)

3. **Clean Module Separation**:
   - `quintet/core/` — Shared types, router (Mode-agnostic)
   - `quintet/builder/` — Build Mode only
   - `quintet/math/` — Math Mode only (imports core types)

4. **One Router**: `UltraModeRouter` in `quintet/core/router.py` is THE router. No other router implementations.

5. **Frozen Contracts**: Key types are now stable:
   - `ModeResultBase`, `ValidationResult`, `ColorTileGrid`
   - `ContextFlowEntry`, `CognitionSummary`, `IncompletenessAssessment`
   - `WorldImpactAssessment`, `ModeError`, `ErrorCode`

### Implementation Order for No-Context AI

```
Phase 1: Tier 0 (Build Mode)
├── 1. Create quintet/core/types.py (shared types)
├── 2. Create quintet/builder/* (detector, spec, executor, ultra_mode, api)
├── 3. Create quintet/core/router.py (with build-only mode)
└── 4. Test: HTTP API works, can create files

Phase 2: Tier 1 (Math Mode Core)
├── 5. Create quintet/math/types.py (math-specific types ONLY)
├── 6. Create quintet/math/backends/{base, sympy_backend, numeric_backend}
├── 7. Create quintet/math/{detector, parser, planner, executor, validator, explainer}
├── 8. Create quintet/math/math_mode.py (orchestrator)
├── 9. Wire MathMode into router
└── 10. Test: Can solve algebra/calculus problems

Phase 3: Tier 2 (Optional)
├── 11. Add optional backends as needed
└── 12. Add Proof Memory, World Impact Auditor, etc.
```

### Key Files Reference

| File | Purpose | Tier |
|------|---------|------|
| `quintet/core/types.py` | **SINGLE SOURCE OF TRUTH** for shared types | 0 |
| `quintet/core/router.py` | UltraModeRouter | 0 |
| `quintet/builder/ultra_mode.py` | Build Mode orchestrator | 0 |
| `quintet/builder/api.py` | HTTP Build API | 0 |
| `quintet/math/types.py` | Math-specific types (imports core) | 1 |
| `quintet/math/math_mode.py` | Math Mode orchestrator | 1 |
| `quintet/math/backends/sympy_backend.py` | SymPy backend | 1 |
| `quintet/math/backends/numeric_backend.py` | NumPy/SciPy backend | 1 |

### Critical Rules

1. **Never duplicate shared types** — Import from `quintet.core.types`
2. **Never create a second router** — Use `UltraModeRouter`
3. **Reference files/types, not section numbers** — Sections drift; code doesn't
4. **Tier 1 must work without Tier 2** — Graceful degradation if optional backends missing

---

## Quintet Decision Graph (v1.2) + Intent/Treaty Examples

The Quintet system follows a canonical decision flow from user intent to execution to learning:

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                          QUINTET DECISION GRAPH                              │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│   ┌──────────────┐                                                          │
│   │  UserIntent  │ ← Raw query from user/system                             │
│   └──────┬───────┘                                                          │
│          │                                                                   │
│          ▼                                                                   │
│   ┌──────────────┐     High-stakes?      ┌───────────────────┐              │
│   │IntentEnvelope│────────────────────────▶│ QuintetCouncil   │              │
│   └──────┬───────┘     Yes (risk/domain)  │ (5 agents vote)  │              │
│          │                                 └────────┬──────────┘              │
│          │ No (low-stakes)                         │                         │
│          │                                         ▼                         │
│          │                                 ┌───────────────────┐              │
│          │                                 │ QuintetSynthesis  │              │
│          │                                 │ (decision+votes)  │              │
│          │                                 └────────┬──────────┘              │
│          │                                         │                         │
│          ▼                                         ▼                         │
│   ┌──────────────────────────────────────────────────────────┐              │
│   │                    UltraModeRouter                        │              │
│   │  (decides: Build Mode vs Math Mode vs Escalate)          │              │
│   └───────────────────────┬──────────────────────────────────┘              │
│                           │                                                  │
│            ┌──────────────┴──────────────┐                                  │
│            ▼                             ▼                                  │
│   ┌─────────────────┐           ┌─────────────────┐                         │
│   │   Build Mode    │           │    Math Mode    │                         │
│   │ (Ultra Mode 2.0)│           │  (Math Mode 3.0)│                         │
│   └────────┬────────┘           └────────┬────────┘                         │
│            │                             │                                   │
│            │    ┌────────────────────────┘                                   │
│            ▼    ▼                                                            │
│   ┌──────────────────────────────────────────────────────────┐              │
│   │                    ValidationResult                       │              │
│   │  (checks, confidence, diversity_score)                   │              │
│   └───────────────────────┬──────────────────────────────────┘              │
│                           │                                                  │
│                           ▼                                                  │
│   ┌──────────────────────────────────────────────────────────┐              │
│   │                      Receipts                             │              │
│   │  - CouncilDecisionReceipt                                │              │
│   │  - BuildReceipt / MathReceipt                            │              │
│   │  - ValidationReceipt                                      │              │
│   └───────────────────────┬──────────────────────────────────┘              │
│                           │                                                  │
│            ┌──────────────┴──────────────┐                                  │
│            ▼                             ▼                                  │
│   ┌─────────────────┐           ┌─────────────────┐                         │
│   │   Guardian      │           │   ProofAtlas    │                         │
│   │   (audit)       │           │   (learning)    │                         │
│   └─────────────────┘           └─────────────────┘                         │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Key Contracts

| Contract | Location | Purpose |
|----------|----------|---------|
| `IntentEnvelope` | `quintet/core/council.py` | Structured user/council intent |
| `QuintetSynthesis` | `quintet/core/council.py` | Council decision + agent votes |
| `Treaty` | `quintet/core/council.py` | Formal agreement for high-stakes flows |
| `RouterDecision` | `quintet/core/router.py` | Mode selection result |
| `ModeResultBase` | `quintet/core/types.py` | Common result envelope |
| `ValidationResult` | `quintet/core/types.py` | Verification outcome |
| `Receipt` | `quintet/core/types.py` | Audit trail artifact |

### Arbitration Policy

```python
# When does council run vs direct routing?

HIGH_STAKES (council required):
  - risk_level in ["high", "critical"]
  - domain in ["healthcare", "finance", "legal", "climate", "humanitarian"]
  - confidence < 0.8

LOW_STAKES (router can bypass council):
  - risk_level in ["low", "medium"]
  - no sensitive domain
  - confidence >= 0.8
  - always_emit_receipts = True (still logged)
```

### Example Flows

**High-Stakes (Math + Build):**
```
User: "Optimize drug dosage for patient cohort and generate deployment code"
  ↓
IntentEnvelope: risk=critical, domain=healthcare, requires_math=True, requires_build=True
  ↓
QuintetCouncil: 5 agents vote, Gamma requests safety checks
  ↓
QuintetSynthesis: decision=proceed, guardrails=[0.95 confidence required], treaty=healthcare-001
  ↓
Router → MathMode (primary) → BuildMode (secondary)
  ↓
Validation: Math=0.96, Build=0.92
  ↓
Receipts: council_decision, math_validation, build_validation, guardian_approval
  ↓
Guardian: Approved (treaty satisfied)
  ↓
ProofAtlas: Strategy genome stored for future healthcare optimization
```

**Low-Stakes (Build only):**
```
User: "Add a helper script to clean old log files"
  ↓
IntentEnvelope: risk=low, requires_build=True
  ↓
[Council bypassed - low stakes]
  ↓
Router → BuildMode directly
  ↓
Validation: Build=0.95
  ↓
Receipts: build_result (council_decision skipped but logged)
```

### Canonical IntentEnvelope + QuintetSynthesis (JSON, high-stakes healthcare)
```json
{
  "intent": {
    "intent_id": "int-health-001",
    "raw_query": "Optimize drug dosage for patient cohort and generate deployment code",
    "proposed_action": "Math optimization + code generation",
    "goal": "Find optimal dosage and create safe deployment pipeline",
    "constraints": ["Must not exceed max safe dose", "Handle edge cases"],
    "invariants": ["Patient safety > optimization accuracy"],
    "risk_level": "critical",
    "world_impact_category": "healthcare_medicine",
    "requires_build": true,
    "requires_math": true,
    "allowed_modes": ["build", "math"]
  },
  "synthesis": {
    "synthesis_id": "syn-health-001",
    "decision": "proceed",
    "confidence": 0.85,
    "requires_build": true,
    "requires_math": true,
    "primary_mode": "math",
    "risk_level": "critical",
    "world_impact_category": "healthcare_medicine",
    "guardrails": [
      "Math Mode must achieve 0.95 confidence",
      "Build Mode must include safety tests",
      "Guardian approval required"
    ],
    "open_questions": ["Provide sensitivity analysis for outlier patients"],
    "votes": [
      {"agent": "alpha", "position": "approve", "confidence": 0.9},
      {"agent": "beta", "position": "approve", "confidence": 0.85},
      {"agent": "gamma", "position": "modify", "confidence": 0.75, "concerns": ["Edge case handling"]},
      {"agent": "delta", "position": "approve", "confidence": 0.9},
      {"agent": "epsilon", "position": "approve", "confidence": 0.85}
    ],
    "dissent": true,
    "dissent_summary": "Gamma requests additional safety validation"
  }
}
```

### Treaty (high-stakes healthcare) — minimal JSON
```json
{
  "treaty_id": "treaty-health-001",
  "name": "Healthcare Deployment Treaty",
  "parties": [
    {"party_id": "guardian", "party_type": "guardian", "role": "veto"},
    {"party_id": "org", "party_type": "system", "role": "operator"}
  ],
  "guarantees": [
    "No deployment without validation receipts",
    "All actions logged for audit"
  ],
  "required_receipts": [
    "math_validation",
    "build_validation",
    "guardian_approval"
  ],
  "veto_conditions": [
    "Validation confidence < 0.95",
    "World impact is critical and treaty missing"
  ],
  "domains": ["healthcare_medicine"],
  "status": "active"
}
```

### Design-time vs Run-time LLM Policy
- **Design-time (default)**: LLMs may draft specs/code/tests/blueprints/contracts, but outputs must pass deterministic checks (validation/tests/Guardian/Math validation).
- **Run-time (opt-in only)**: Allowed solely via an explicit `MODEL_CALL` entry inside `IntentEnvelope`/`QuintetSynthesis`, requires Guardian approval and emits receipts. If not present/approved, run-time LLM calls are blocked.

---

## Original Spec (Below)

> The following sections contain the detailed spec. When in doubt, the v1.1/v1.2 Overview above takes precedence.

Target location on the new machine (example OSX user `tim`):

- Recommended path: `/Users/tim/loom`
- This document path: `/Users/tim/loom/docs/QUINTET_ULTRA_MODE_REPLICATOR.md`
- Full file URL: `file:///Users/tim/loom/docs/QUINTET_ULTRA_MODE_REPLICATOR.md`

Any AI following this spec should be able to:

- Recreate the **Quintet** orchestrator package (5-agent council, semantic memory, etc. — high level only here).
- Recreate the **Ultra Mode 2.0 builder stack**:
  - Build intent detector (“Eyes”).
  - Context-aware spec generator (“Brain”).
  - Executor with validation and rollback (“Hands”).
  - Ultra Mode OODA loop orchestrator.
  - HTTP Build API server.
- Wire these pieces so that:
  - Quintet can call Ultra Mode using the `synthesis` object.
  - A frontend (or another agent) can talk to the builder over HTTP.

---

## 1. High-Level Architecture

Conceptual diagram:

- **Quintet Council**: Multi-agent deliberation engine (Alpha/Beta/Gamma/Epsilon/Delta). Produces a *synthesis* object that may include `"build_specification"` and `"actionable_outputs"`.
- **Ultra Mode Orchestrator** (`UltraModeOrchestrator`):
  - OBSERVE: Use `BuilderDetector` to decide if a user query is a “build” request.
  - ORIENT: Use `SpecGenerator` to scan the project tree and detect patterns.
  - ARCHITECT: Generate a `ProjectBlueprint` (goal, files, shell commands, test plan, risks).
  - DECIDE: Optionally ask for approval (`on_blueprint_ready` hook).
  - ACT: Use `BuilderExecutor` to apply the blueprint and validate output.
  - LOOP: Retry failed builds up to `max_retries` with optional correction hook (`on_error`).
- **HTTP Build API** (optional but recommended):
  - Thin server exposing `/detect`, `/blueprint`, `/build`, `/full`.
  - Uses the same detector/architect/executor as Ultra Mode.

The key design principles:

- **Context-first**: The builder scans the project before writing code (solves “blind surgeon”).
- **Validation-first**: The executor validates artifacts (syntax, imports, existence) and can run tests.
- **Fail-closed**: Uncertain or failing builds are surfaced as errors, not silently handed to the user.

---

## 2. Directory Layout on the New Machine

On the new machine, create this minimal structure:

```text
/Users/tim/loom/
  docs/
    QUINTET_ULTRA_MODE_REPLICATOR.md
  quintet/
    __init__.py
    core.py                 # (Quintet orchestrator – high-level placeholder acceptable)
    builder/
      __init__.py
      detector.py           # Build intent detector
      specification.py      # Context-aware spec generator
      executor.py           # Executor + validation
      ultra_mode.py         # OODA loop orchestrator
      api.py                # HTTP Build API server
```

The **Quintet non-builder pieces** (`core.py`, agents, memory) can be ported or re-implemented separately; this spec focuses on the **builder + Ultra Mode** and how to integrate it.

---

## 3. Environment and Dependencies

On the new machine:

1. Install Python 3.10+.
2. Create and activate a virtual environment:

   ```bash
   cd /Users/tim/loom
   python3 -m venv .venv
   source .venv/bin/activate
   ```

3. Install baseline dependencies (keep minimal for portability):

   ```bash
   pip install fastapi pydantic pytest
   ```

   - `fastapi` / `pydantic` are used in generated API skeletons (spec generator).
   - `pytest` is used for generated tests and for the test plan command.

4. Optional (for Quintet integration): install your LLM client and any semantic-memory backend the council uses. This spec does not assume a particular provider.

---

## 4. Core Builder Components (What to Recreate)

This section describes each core module and its contract so a no-context AI can reconstruct them.

### 4.1 `builder/detector.py` – Build Intent Detector (“Eyes”)

Purpose:

- Decide when a query should trigger **build mode** vs. normal “explain/answer” behavior.

Key types:

- `BuildIntent` dataclass:
  - `is_buildable: bool`
  - `confidence: float` (`0.0–1.0`)
  - `artifact_types: List[str]` (e.g., `"module"`, `"test"`, `"api"`, `"cli"`)
  - `language: str` (e.g., `"python"`, `"javascript"`)
  - `complexity: str` (`"simple" | "moderate" | "complex"`)
  - `keywords_matched: List[str]`

- `BuilderDetector`:
  - Contains keyword lists for:
    - **BUILD_VERBS** (build, create, implement, write, generate, etc.).
    - **ARTIFACT_KEYWORDS** (module, test, api, cli, config, database, frontend, pipeline).
    - **LANGUAGE_KEYWORDS** (python, javascript, typescript, react, yaml, sql, rust, go).
    - **ANALYSIS_KEYWORDS** (explain, what is, compare, why, best practices, etc.).
  - `detect(query: str, synthesis: Optional[Dict[str, Any]]) -> BuildIntent`:
    - Uses regex to find build verbs and analysis verbs.
    - If `synthesis` is provided, checks:
      - `synthesis["actionable_outputs"]`
      - `synthesis["build_specification"]["buildable"]`
    - Infers artifact types and language from keywords.
    - Estimates complexity from word count and number of artifacts.
    - Computes `confidence` by scoring: +0.35 (build verbs), +0.25 (actionable build), +0.20 (artifact types), +0.10 (multi-artifact), −0.25 (analysis verbs).
    - Sets `is_buildable` if `confidence >= 0.4`.
  - `should_build(intent: BuildIntent) -> bool`: simple predicate using the same threshold.

**Slight improvement suggestion** (when recreating):

- Add a configurable threshold (e.g. `min_confidence`) and a hook to allow downstream systems to override or force build mode in special cases.

### 4.2 `builder/specification.py` – Spec Generator (“Brain”)

Purpose:

- Scan the project directory, infer language/framework patterns, and generate a **ProjectBlueprint**.

Key types:

- `FileSpec`:
  - `path: str`
  - `content: str`
  - `description: str`
  - `action: str = "create"` (`"create" | "modify" | "delete"`)
  - `dependencies: List[str]`
  - `test_criteria: List[str]`

- `ProjectBlueprint`:
  - `goal: str`
  - `rationale: str`
  - `new_files: List[FileSpec]`
  - `modifications: Dict[str, str]` (instructions for existing files)
  - `shell_commands: List[str]` (e.g., `mkdir -p`, `pip install ...`)
  - `test_plan: str` (shell command to verify success)
  - `estimated_complexity: str`
  - `estimated_files: int`
  - `risks: List[str]`
  - Metadata: `generated_at`, `blueprint_id`.
  - Methods: `to_dict()`, `to_json()`.

- `ProjectContext`:
  - `root_dir: str`
  - `tree_summary: str` (ASCII tree, limited depth)
  - `file_count: int`
  - `detected_language: str`
  - `detected_framework: Optional[str]`
  - `existing_patterns: List[str]`
  - `key_files: Dict[str, str]` (filename → first ~1000 chars).

- `SpecGenerator(root_dir: str)`:
  - `scan_context(max_depth: int = 4) -> ProjectContext`:
    - Walks the filesystem from `root_dir`.
    - Skips ignored dirs: `.git`, `__pycache__`, `venv`, `.venv`, `node_modules`, etc.
    - Builds a small tree representation and counts files.
    - Detects language and frameworks using `FRAMEWORK_PATTERNS` against key files.
  - `generate_blueprint(query: str, context: Optional[ProjectContext], synthesis: Optional[Dict[str, Any]]) -> ProjectBlueprint`:
    - Inspect `query` for simple indicators:
      - API → `_spec_api_endpoint()` (+ optional `_spec_api_test()`).
      - Module/class → `_spec_module()` + `_spec_module_test()`.
      - CLI → `_spec_cli()`.
      - Test → `_spec_test()`.
      - Default: basic module.
    - Adds `shell_commands` for needed directories (`mkdir -p`).
    - Builds a test plan:
      - If any new file under `tests/` → include `pytest -v`.
      - Else possibly include a basic sanity command.
    - Estimates complexity and risks heuristically (based on file count/artifacts).
  - Helper methods like `_spec_module`, `_spec_api_endpoint`, `_spec_cli`, `_spec_test`, `_extract_name`, `_extract_goal`.

**Slight improvement suggestion**:

- Allow injecting an **LLM planner** that receives `ProjectContext` + query and returns a richer blueprint; keep the current heuristic generator as a fallback.

### 4.3 `builder/executor.py` – Builder Executor (“Hands”)

Purpose:

- Take a `ProjectBlueprint` (as JSON) and make it real:
  - Create/modify/delete files.
  - Run shell commands.
  - Validate artifacts (existence, non-empty, syntax/import checks).
  - Optionally run test plan.

Key types:

- `ValidationResult`:
  - `artifact_path: str`
  - `passed: bool`
  - `checks: List[Dict[str, Any]]` (name, passed, output)
  - `error_message: Optional[str]`

- `BuildResult`:
  - `success: bool`
  - `files_created: List[str]`
  - `files_modified: List[str]`
  - `commands_run: List[Dict[str, Any]]`
  - `validations: List[ValidationResult]`
  - `errors: List[str]`
  - `execution_time_ms: float`
  - `rollback_available: bool`
  - `to_dict()`.

- `BuilderExecutor(root_dir: str = ".", dry_run: bool = False)`:
  - `execute(blueprint_json: str) -> BuildResult`:
    - Parses JSON.
    - If not `dry_run`, prepares a backup directory (for potential rollback).
    - Runs each shell command via `_run_command`.
    - For each file spec:
      - `action == "create"` → `_create_file`.
      - `action == "modify"` → `_modify_file`.
      - `action == "delete"` → `_delete_file`.
    - Validates each created file with `_validate_file`.
    - If `test_plan` and not `dry_run`, executes the test plan.
    - Aggregates errors and determines `success`.
  - `_run_command(cmd: str, timeout: int = 60) -> Dict[str, Any]`:
    - Uses `subprocess.run` with `cwd=root_dir`, captures stdout/stderr (truncated).
    - In `dry_run`, returns a synthetic success result.
  - `_create_file`, `_modify_file`, `_delete_file`:
    - Create dirs, write files, copy to backup before modifying or deleting (if backup exists).
  - `_validate_file(path: Path, test_criteria: List[str]) -> ValidationResult`:
    - `file_exists` check.
    - `not_empty` check.
    - For `.py` files: `_check_python_syntax` using `py_compile`.
    - For `.py` files: `_check_python_imports` via `compile(content, path, 'exec')`.
  - `rollback()`:
    - Uses backup dir to restore state (simplified in current version; can be improved).

**Slight improvement suggestion**:

- Track original paths and full backup metadata so rollback can faithfully restore files rather than just logging.

---

## 5. Ultra Mode Orchestrator (`builder/ultra_mode.py`)

Purpose:

- Implement the OODA loop (“Nervous System”) that ties detector, spec generator, and executor together.

Key elements:

- `UltraModeResult`:
  - `success: bool`
  - `mode_triggered: bool`
  - `intent: Optional[BuildIntent]`
  - `blueprint: Optional[ProjectBlueprint]`
  - `build_result: Optional[BuildResult]`
  - `iterations: int`
  - `total_time_ms: float`
  - `conversation_response: str`
  - `to_dict()`.

- `UltraModeOrchestrator`:
  - `__init__(root_dir=".", max_retries=2, auto_approve=False, dry_run=False)`:
    - Creates:
      - `self.detector = BuilderDetector()`
      - `self.architect = SpecGenerator(root_dir)`
      - `self.executor = BuilderExecutor(root_dir, dry_run)`
    - Hooks:
      - `self.on_blueprint_ready: Optional[Callable[[ProjectBlueprint], bool]]`
      - `self.on_error: Optional[Callable[[str, List[str]], str]]`
  - `process(query: str, synthesis: Optional[Dict[str, Any]] = None) -> UltraModeResult`:
    - Logs “Ultra Mode 2.0” header and query.
    - **OBSERVE**: `intent = detector.detect(query, synthesis)`; if not buildable:
      - Return `UltraModeResult(success=True, mode_triggered=False, ...)` with conversational fallback.
    - **ORIENT**:
      - `context = architect.scan_context()`
      - `blueprint = architect.generate_blueprint(query, context, synthesis)`
    - **DECIDE**:
      - If `auto_approve` is `False` and `on_blueprint_ready` is set:
        - Call the hook; if it returns `False`, abort with no changes.
      - Else: auto-approve.
    - **ACT + LOOP**:
      - For `iteration` in `1 .. max_retries+1`:
        - Run `executor.execute(blueprint.to_json())`.
        - If success → break.
        - If failure and retries remain:
          - If `on_error` hook is set, call it with `(query, errors)` for hints (future versions can modify blueprint).
          - Log top error messages.
    - Build `conversation_response` summarizing:
      - Files created, test plan, execution time on success.
      - Errors and advice on failure.
    - Return the `UltraModeResult`.
  - `process_with_synthesis(query: str, quintet_output: Dict[str, Any]) -> UltraModeResult`:
    - Reads `build_specification` from `quintet_output` (if present) and passes the full synthesis through to `process()`.

- Factory:

  ```python
  def create_ultra_orchestrator(root_dir=".", auto_approve=False, dry_run=False) -> UltraModeOrchestrator:
      return UltraModeOrchestrator(root_dir=root_dir, max_retries=2, auto_approve=auto_approve, dry_run=dry_run)
  ```

**Slight improvement suggestion**:

- Allow dynamic adjustment of `max_retries` and `dry_run` per request using fields in the `synthesis` or via explicit API options.

---

## 6. HTTP Build API (`builder/api.py`)

Purpose:

- Provide a minimal HTTP server so frontends or other agents can use Ultra Mode without embedding it directly.

Key pieces:

- Module-level imports:
  - Adds builder directory to `sys.path` so it can import `detector`, `specification`, and `executor` directly.
  - Imports:
    - `BuilderDetector`, `BuildIntent`
    - `SpecGenerator`, `ProjectBlueprint`
    - `BuilderExecutor`, `BuildResult`

- `BuilderAPIHandler(BaseHTTPRequestHandler)`:
  - Class attributes:
    - `detector`, `architect`, `executor`
    - `root_dir`, `dry_run`
    - `start_time`, `request_count`, `failure_count`, `last_error`
  - `initialize(root_dir: str = ".", dry_run: bool = False)`:
    - Instantiates detector/architect/executor, resets counters.
  - `send_json(data, status=200)`: JSON response + CORS headers.
  - `do_OPTIONS()`: CORS preflight.
  - `do_GET()`:
    - `/` → redirects to a UI (not strictly required; you can customize).
    - `/health` → status JSON (uptime, requests, failures).
    - `/status` → readiness + root dir.
    - Else → attempts to serve static files from `root_dir`, with basic caching headers.
  - `do_POST()`:
    - Parses JSON body.
    - Routes to:
      - `/detect` → `handle_detect`
      - `/blueprint` → `handle_blueprint`
      - `/build` → `handle_build`
      - `/full` → `handle_full`
  - `handle_detect`:
    - Input: `{ "query": "...", "synthesis": {...} }`
    - Output: `BuildIntent.to_dict()`.
  - `handle_blueprint`:
    - Input: `{ "query": "...", "synthesis": {...} }`
    - Calls `scan_context()` and `generate_blueprint()`.
  - `handle_build`:
    - Input: `{ "blueprint": {...} }`
    - Calls `executor.execute(json.dumps(blueprint))`.
  - `handle_full`:
    - Full pipeline: detect → blueprint → build in one call.

- `run_server(host="localhost", port=8888, root_dir=".", dry_run=True)`:
  - Initializes handler and starts `HTTPServer`.
  - Prints endpoints and server URL.

- CLI entrypoint (`if __name__ == "__main__":`):
  - Parses `--host`, `--port`, `--root`, `--no-dry-run`.
  - Calls `run_server(...)`.

**Slight improvement suggestion**:

- Add a simple authentication layer or IP allow-list for non-local deployments.

---

## 7. Rebuild Steps for a No-Context AI

Assuming the AI only has this document and a blank `/Users/tim/loom` directory:

1. **Create directories**:

   ```bash
   mkdir -p /Users/tim/loom/docs
   mkdir -p /Users/tim/loom/quintet/builder
   ```

2. **Write this document** to:

   - `/Users/tim/loom/docs/QUINTET_ULTRA_MODE_REPLICATOR.md`

3. **Create minimal `__init__.py`** files:

   - `/Users/tim/loom/quintet/__init__.py`:

     ```python
     # Quintet package marker; core orchestrator lives in core.py
     ```

   - `/Users/tim/loom/quintet/builder/__init__.py`:

     ```python
     # Builder (Ultra Mode 2.0) package marker
     ```

4. **Implement** the modules exactly as described in sections 4–6:

   - `detector.py` with `BuildIntent` and `BuilderDetector`.
   - `specification.py` with `FileSpec`, `ProjectBlueprint`, `ProjectContext`, `SpecGenerator`.
   - `executor.py` with `ValidationResult`, `BuildResult`, `BuilderExecutor`.
   - `ultra_mode.py` with `UltraModeResult`, `UltraModeOrchestrator`, `create_ultra_orchestrator`.
   - `api.py` with `BuilderAPIHandler`, `run_server`, and the CLI entrypoint.

5. **Create a lightweight `core.py`** in `quintet/` that can, at minimum:

   - Call the builder via:

     ```python
     from quintet.builder.ultra_mode import create_ultra_orchestrator
     ```

   - Pass the **Grand Synthesis** (if available) into `process_with_synthesis`.

6. **Set up Python environment and dependencies** as in section 3.

7. **Run a smoke test**:

   - Direct orchestrator:

     ```bash
     cd /Users/tim/loom
     python -m quintet.builder.ultra_mode
     ```

     Expect: log output for several test queries, indicating which ones triggered build mode and whether they succeeded (in `dry_run` by default).

   - HTTP API:

     ```bash
     cd /Users/tim/loom
     python -m quintet.builder.api --host localhost --port 8888 --root .
     ```

     Then, from another shell or client:

     ```bash
     curl -X POST http://localhost:8888/full \
       -H "Content-Type: application/json" \
       -d '{"query": "Build me a Python module with tests"}'
     ```

     Expect: JSON response with `mode_triggered: true`, a blueprint, and a `build_result`.

---

## 8. File URL and Hand-Off

On the **new machine**, once this document is placed at:

- Path: `/Users/tim/loom/docs/QUINTET_ULTRA_MODE_REPLICATOR.md`

The full file URL is:

- `file:///Users/tim/loom/docs/QUINTET_ULTRA_MODE_REPLICATOR.md`

Any no-context AI bootstrapping in that environment can:

- Read this document.
- Recreate the directory layout.
- Implement the described modules and classes.
- Start the Ultra Mode 2.0 builder and connect it to Quintet or any other multi-agent system.

This is the **canonical build/spec contract** for the Quintet + Ultra Mode architecture on the new machine.

---

## 9. Ultra Mode–First Strategy (5×–10× Upgrade)

When the new machine has zero Quintet artifacts, treat Ultra Mode 2.0 as the **primary system** rather than the bolt-on. The goal is to recreate an ecosystem where Ultra Mode is the *only* interface the user or AI ever sees, and the council, agents, and semantic layers are tightly scoped to feed it. Make this redesign “literally 5 to 10x better” by applying these upgrades:

1. **Single-loop authority**: Drop the assumption that Quintet orchestrates Ultra Mode. Instead, Ultra Mode **owns the discovery** process and when deeper reasoning is required it **delegates to a trimmed council** (Alpha/Beta/Gamma only) that streams summaries via the `synthesis` object when needed. This cuts context switches and keeps Ultra Mode lean.
2. **Goal-weighted context scanning**: Extend `SpecGenerator.scan_context()` to treat files and directories as **weighted tiles** (more detail in section 10). Track a `context_flow` list that records how each directory influenced the decision, e.g., `["src/routes (api) → tests (validation) → infra (deploy)"]`. Use that flow log in blueprints to convey nuance like “approach relies on existing API directory, so risks include coupling to routes/”. This is the “flow” riddle solution—context is a stream that must never break.
3. **Contradiction Resolver**: Introduce a validator that tracks contradictions between user intent, existing files, and Ultra Mode assumptions. For example, if the query asks for “build an AI safety guardrail” but the project already has a `guardian` module flagged for a different purpose, the resolver surfaces a flagged contradiction and prompts the `on_error` hook with a question. This addresses “contradiction” by making contradictions first-class data that trigger clarifying loops rather than failing silently.
4. **Recursive self-improvement**: After each build, run a meta-check that reviews `build_result` and `blueprint` for structural patterns. If the blueprint included multiple files touching the same namespace, automatically create a `blueprint.postmortem` entry that the next run can read and treat as a recursion seed (e.g., “failure happened because CLI and API used different config values; next build should reconcile via shared config class”). This recursion-aware memory feeds into the `context_flow` log.
5. **Incompleteness Graceful Degradation**: Recognize that Ultra Mode cannot always finish the overall system; sometimes partial artifacts are acceptable. Track `incompleteness_score` in `ProjectBlueprint` (0–1) indicating how much of the stated goal was concretely produced. When a build hits high risk (heavy shell commands, unknown frameworks), set the score low and include a “next steps” section in the blueprint so the user understands what remains. This solves the “incompleteness” riddle elegantly.
6. **Cognition-rich logging**: Every iteration writes a short `cognition_summary` (3 sentences) highlighting what was observed/oriented versus what changed due to action. Store these summaries alongside the blueprint’s metadata, so future Ultra Mode invocations can read them and avoid repeating the same reasoning. This adds subtlety and sophistication.

These features require modest extensions to existing modules (new fields, extra helper methods) but they multiply Ultra Mode’s value by letting it self-correct, explain, and anticipate contradictions before they cause failure. The new Quintet council simply becomes a **reasoning stretch goal** that reuses the cognitive summaries when invoked.

## 10. Cool Color Tile Specification (post-Ultra Mode highlight)

At the end of each Ultra Mode run (success or failure), present a **Cool Color Tile Layout** that encodes the build’s emotional + technical signature. It is both an aesthetic output and a structured spec that the next Ultra Mode run can interpret.

### Tile grid

- Layout: 3 rows × 3 columns (9 tiles).
- Each tile is defined by:
  - `tile_id` (row-col, e.g., `A1`, `C3`).
  - `color` (hex string) chosen from a palette tied to build phases.
  - `mood` (short string such as `calm`, `alert`, `curious`).
  - `signal` (one of `success`, `warning`, `error`, `waiting`).
  - `data_reference` (pointer to specific artifact or message, e.g., `blueprint.new_files[1]` or `build_result.errors[0]`).

### Phase colors

1. **Observation row (A1–A3)**: Palette = soft blues; one tile per observation signal (detector confidence, context_flow summary, contradictions_count).
2. **Orientation row (B1–B3)**: Palette = violet gradients; track blueprint density, complexity, and incompleteness_score.
3. **Action row (C1–C3)**: Palette = greens/oranges; map to build success, validation pass rate, and recommended next steps (tile C3 contains a mini “storyline” string).

### Behavior

- Resolve the “color tile” spec by emitting a JSON snippet appended to the `UltraModeResult.conversation_response` as a code block.
- Each tile entry must include a short `tagline`: two words that capture the nuance (e.g., `A2`: `“Aware Flow”`, `B1`: `“Architected Intuition”`).
- Add a helper `UltraModeOrchestrator.render_color_tiles()` that consumes `intent`, `blueprint`, `build_result`, and `context_flow`, then yields the 3×3 grid.
- The coolest innovation is letting future runs treat the tile grid as a **semi-structured knowledge artifact**; for example, if tile B3 warns `incomplete` for dependency installation, the next build can preemptively flag `shell_commands` to install packages.

This color tile “ending” becomes the last visible thing in the conversation so users get an elegant, cognition-informed sensory summary every time. It doubles as documentation for “what just happened” and a structured spec for what to watch next.

## 11. Riddle Solutions (Contradiction, Recursion, Incompleteness, Flow)

To satisfy the riddles you mentioned:

- **Contradiction**: Represent contradictions as list entries from `SpecGenerator`. Each contradiction is a tuple `(topic, expected_state, current_state)` that is surfaced before executing shell commands. When contradictions exist, Ultra Mode halts after validation and offers a `resolve` prompt, storing the tuple in `context_flow` so future runs know what to avoid.
- **Recursion**: Build the recursion pattern by storing `blueprint.metadata["recursion_seed"]` anytime Ultra Mode reuses a blueprint that failed. The seed includes the key difference between iterations (error message vs. fix attempt) so subsequent runs can treat the failure as an input. This turns recursion from a bug into a creative improvement loop.
- **Incompleteness**: The `incompleteness_score` (0.0–1.0) is output alongside the cool color tiles (tile B3). If the score is below 0.7, Ultra Mode will not auto-approve future builds in the same session; instead it adds a `next_steps` note describing what remains (manually reviewed docs, integration testing, etc.).
- **Flow**: The `context_flow` log is a chronological trail of directories/files/actionable decisions. Every `ProjectBlueprint` includes:

  ```json
  "context_flow": [
    "observe: src/routes (api) → orient: tests (validation)",
    "observe: infra/ops (deploy) → act: blueprint modifies build scripts"
  ]
  ```

  When Ultra Mode processes a new query, it reads `context_flow` excerpts from the latest successful build (if available) and biases the detector/architect choices accordingly. This ensures the flow never breaks and gives a sense of narrative continuity.

These mechanisms promote nuance, subtlety, and sophistication, turning Ultra Mode into a cognitive system that can explain what it knows, what it doubts, and what it will try next.

## 12. Elegant Next Steps

After the machine rebuild and Ultra Mode redesign, you may want to:

1. Provide a simplified Quintet `core.py` that exports `process_with_synthesis` and optionally a `QuintetCouncil` stub using the new `context_flow`/tile metadata.
2. Extend the HTTP API to return the color tile grid via `/status` for dashboards.
3. Bake the new contradiction/resolution data into any downstream UI so the AI can ask clarifying questions before acting.

Every new run should feel like “the same Ultra Mode, but smarter, more aware, more elegant.”

## 13. Deep Researcher Interface Blueprint

To make the system “the ultimate deep researcher,” treat the UI as a living cockpit that keeps curiosity, traceability, and organism feedback tightly bound. Aim for three synchronized panels plus ambient feedback:

1. **Perception Console (left column)**  
   - Displays the latest `UltraModeResult.intent`, `confidence`, `context_flow`, and contradictions flagged by the SpecGenerator.  
   - Includes a real-time transcript of perception events (detector triggers, file insights, contradiction resolutions) so researchers can audit what the builder “saw.”  
   - Offers filters by artifact type and language, and lets the user pin context snippets for later reference.

2. **Action Navigator (center column)**  
   - Renders the latest `ProjectBlueprint` sections (`goal`, `rationale`, `shell_commands`, `tests`, `next_steps`).  
   - Shows the `color tile grid` (from section 10) as a interactive heat map; clicking a tile drills into its `data_reference` (e.g., file or error).  
   - Surfaces `cognition_summary` plus `incompleteness_score` so users see exactly what remains to be done and why Ultra Mode hesitated (if applicable).  
   - Includes multi-step timeline of `blueprint.postmortem` seeds to highlight recursive learning loops.

3. **Organism Feedback Channel (right column)**  
   - Streams Guardian/Council receipts tied to the current build (Guardian verdicts, proof tier, ΔC signals, Ωᴴ events).  
   - Visualizes attestor alerts, tool safety blocks, and PolicyTuner notifications that affect the Ultra Mode session.  
   - Exposes quick actions to surface context to the organism (e.g., "Request Guardian Expansion" or "Send Cognitive Summary to Council").

Surround these panels with ambient HUD elements:

- **Semantic search bar** connected to `MemoryGraph`/Atlas so the researcher can drag an entity (e.g., “clinical guardian”) into the builder and have Ultra Mode bias the spec accordingly.  
- **Color tile overlay** that pulses according to the latest `signal` (from section 10) and anchors the sensory experience.  
- **Episode timeline footer** that shows recent decisions, receipts, and reconciliation statuses from the organism (with deep links to `docs/episodes/` if present).

This UI should communicate both what was built and the organism’s state; color-coded signals let the researcher sense Alignment (green), Warning (amber), or Critical (red) without parsing logs.

## 14. Best-in-Class Architecture Upgrades

To make this architecture “better than anything else,” mandate the following cross-cutting capabilities:

1. **Unified Traceability Fabric**: Every action (detector event, blueprint change, executor command, UI interaction) writes a receipt that includes `blueprint_id`, `context_flow`, `color_tile` tags, and `cognition_summary`. Store receipts in a queryable ledger so dashboards, Organism HUD, and research UI can replay the same reasoning path.
2. **Organism Relay Layer**: Build a small middleware that listens to Ultra Mode emissions and translates them into organisms signals (Guardian/ΔC, ProofProfile updates, Omega-H adjustments). This relay keeps the organism responsive even before the full Quintet council is ported.
3. **Experience Mesh**: Deploy a simple event bus (Kafka/Redis PubSub/local AsyncIO channel) between the HTTP API, UI frontend, and any agent loops. Every `build_result` publishes updates to UI subscribers and the relay layer simultaneously.
4. **Adaptive Hardening**: Use the `incompleteness_score`, `contradiction` list, `context_flow`, and `color_tile` warnings to automatically escalate builds (e.g., fail to Guardian review when incompleteness is too high or contradictions unresolved). This ensures the UI and organism never see ambiguous states.
5. **Researcher Inference Hooks**: Allow the UI to send clarifying questions back through the API (e.g., “why was the context_flow weighting shifted to infra?”). Ultra Mode exposes `hooks["researcher_clarify"]` that can either re-run detection or prompt a human-in-the-loop before continuing.

These upgrades ensure the builder, UI, and organism form a cohesive “conscious” research platform—transparent, responsive, and trustworthy.

## 15. Implementation Playbook

To execute the vision:

1. **Prototype the UI** with static JSON fixtures derived from the document (context_flow, color tiles, blueprint). Build a lightweight `ui/` directory with sample HTML/JS or markdown wireframes to capture layout and interaction details.
2. **Gate the backend**: Implement the new metadata (context_flow, contradictions, incompleteness_score, cognition_summary) in `builder/specification.py` and `builder/ultra_mode.py`, keeping tests for each field. Instrument the HTTP API to return the enriched Ultra Mode result plus tile grid via `/status`.  
3. **Connect to the organism**: Build the relay layer that converts Ultra Mode emissions into receipts/Guardian updates. Launch the `tools/audit/attestor` to consume these receipts and flag anomalies for the UI.
4. **Run research scenarios**: Use the upgraded UI and API to run “deep researcher sessions” (e.g., exploring clinical guardrails, architectural refactors). Confirm the UI color tiles align with build outcomes and organism events.  
5. **Document the best-in-world story**: Keep expanding this doc with case studies, UX requirements, and organism contracts as you iterate, so the next collaborator sees exactly how the pieces fit together.

With this dual strategy the repository becomes a living research OS: Ultra Mode powers the cognition, the UI surfaces the depth, and the organism ensures constitutional trust. Let me know if you'd like me to scaffold the UI/relay code next or keep refining the spec further.

---

## 16. Math Mode 3.0 — Research‑Grade Reasoning Engine

> *Handle everything from GSM8K‑style homework up through MATH, AIME, Olympiad/Putnam‑level problems, and applied PDE/optimization/ML/stats problems that show up in real research & engineering.*

Math Mode 3.0 transforms Ultra Mode into a **research-grade reasoning engine** capable of solving mathematical problems with real compute, verification, and world-impact awareness. Not just "produce plausible steps", but:

- **Verified** (symbolic, numeric, statistical, or formal where possible)
- **Backed by actual compute** (solvers, optimizers, PDE engines, ML code)
- **Honest about uncertainty** and impact

This mirrors how state‑of‑the‑art systems like AlphaGeometry/AlphaProof and recent Olympiad‑level systems combine search + symbolic reasoning + heavy test‑time compute, rather than just one-pass CoT.

### 16.1 Core Principles (Research-Grade)

1. **Code-as-proof default.** Whenever possible, Math Mode represents reasoning as **executable code** (SymPy scripts, JAX/PyTorch functions, CVXPY models, FEniCS/Firedrake PDE scripts, statsmodels fits). Solutions are treated as *programs that can be checked*, similar in spirit to SymCode's "math via verifiable code generation".

2. **Multi‑backend solving.** Every serious problem can go through **several backends**: symbolic (SymPy), numeric (SciPy/JAX), optimization (CVXPY), stats (statsmodels, scikit‑learn), ML (PyTorch/JAX), PDE (FEniCS/Firedrake).

3. **Subgoal‑first planning.** Use a SEGO‑style "generate → optimize → select" subgoal planner, with explicit DAG structure for steps.

4. **Verification‑first, not answer‑first.** Every candidate solution goes through a **stack of verifiers**: substitution, numerical spot‑checks, alternative methods, domain‑specific sanity, and (optionally) formal proof. This mirrors chain‑of‑verification, self‑consistency, forward/backward reasoning, and Math‑Shepherd style process checking.

5. **Compute‑scalable.** The system explicitly exposes **compute budgets / test‑time compute** knobs so you can do "IMO gold medal" style deep search when needed, like recent gold‑medal AI systems and experimental ultra‑reasoners.

6. **World‑impact aware.** Problems involving climate, healthcare, logistics, fairness, etc. are tagged and get stricter verification / more conservative confidence.

### 16.2 Directory Layout (Extended)

```text
quintet/
  math/
    __init__.py
    detector.py          # MathIntent
    parser.py            # MathProblem / DataProblem
    planner.py           # SolutionPlan / subgoal DAG
    executor.py          # MathExecutor (multi-backend)
    validator.py         # MathValidator
    explainer.py         # MathExplainer
    math_mode.py         # MathModeOrchestrator
    backends/
      __init__.py
      sympy_backend.py
      numeric_backend.py
      optimization_backend.py
      stats_backend.py
      ml_backend.py
      pde_backend.py
      sampling_backend.py
      lean_backend.py      # optional
      wolfram_backend.py   # optional
    domains/
      __init__.py
      algebra_calc.py
      prob_stats.py
      ml_opt.py
      physics_pde.py
      algorithms_cs.py
    problems/
      __init__.py
      taxonomy.py
      world_impact.py
    eval/
      __init__.py
      benchmarks.py     # harness for MATH, GSM8K, AIME, OlympiadBench...
      runners.py
```

This keeps domain‑specific logic in `domains/` and heavy tooling in `backends/` instead of overloading the core orchestrator.

---

## 17. Dependencies (Base + Power Packs)

### 17.1 Base (Required)

```bash
pip install sympy numpy scipy matplotlib
```

- **SymPy** – symbolic math engine
- **NumPy/SciPy** – numeric linear algebra, optimization, ODE solvers
- **Matplotlib** – visualization

### 17.2 Optimization Pack (Recommended)

```bash
pip install cvxpy
```

**CVXPY** is the standard Python DSL for convex optimization, widely used in ML, control, finance, resource allocation.

### 17.3 Stats / Probability / Traditional ML Pack (Recommended)

```bash
pip install scikit-learn statsmodels
```

- **scikit‑learn** – classic ML algorithms, preprocessing, model selection
- **statsmodels** – serious stats & econometrics (GLMs, time series, hypothesis tests)

For Bayesian / probabilistic programming (optional but powerful):

```bash
pip install numpyro
```

**NumPyro** gives you JAX‑accelerated HMC/NUTS and generative modeling.

### 17.4 Deep Learning / JAX Pack (Recommended for ML/Physics)

```bash
pip install torch jax jaxlib
```

- **PyTorch** – dominant deep learning framework
- **JAX** – high‑performance autodiff / array computing, great for scientific computing and PDEs

### 17.5 PDE / Physics Pack (Optional "Power Pack")

PDE solving libraries are heavy; treat them as optional:

```bash
# FEniCS (recommended for serious PDE work)
# See: https://fenicsproject.org/download/

# Or Firedrake
# See: https://www.firedrakeproject.org/download.html
```

- **FEniCS / FEniCSx** – finite element PDE platform in Python
- **Firedrake** – another automated finite element system

### 17.6 Formal Verification Pack (Optional)

```bash
# Lean 4 (requires separate installation)
# See: https://leanprover.github.io/lean4/doc/setup.html
```

Backends should **probe for availability** and degrade gracefully when optional packages aren't installed.

---

## 18. Core Types & Modules

### 18.1 `MathIntent` (Enhanced)

```python
@dataclass
class MathIntent:
    is_math: bool
    confidence: float
    problem_type: str      # algebra, calculus, probability, statistics, optimization,
                           # differential_equations, linear_algebra, geometry, proof,
                           # word_problem, ml_training, algorithm_analysis, ...
    difficulty: str        # basic | intermediate | advanced | research
    requires_symbolic: bool
    requires_numeric: bool
    requires_formal: bool
    requires_data: bool          # NEW: needs dataset/experiments
    requires_code_exec: bool     # NEW: needs to run actual code
    domain: str                  # pure_math | stats | ml | physics | algorithms | finance | other
    world_impact_category: Optional[str]
    time_budget_ms: Optional[int]   # soft hint for compute
    compute_tier: str               # "light" | "standard" | "deep_search"
    keywords_matched: List[str]
```

**MathDetector** upgrades:

- Understand LaTeX, ASCII math, AND code‑like snippets (`def f(x): return x**2`)
- Recognize data/experiment phrases ("fit a logistic regression to…", "train a neural network…", "simulate this SIR model")
- Map to **domains**:
  - "p‑value", "regression", "ARIMA" → `domain="stats"`, `requires_data=True`
  - "train", "gradient descent", "transformer", "loss" → `domain="ml"`, `requires_code_exec=True`
  - "Poisson equation", "Navier–Stokes", "finite elements" → `domain="physics"`, `requires_numeric=True`, `requires_code_exec=True`
  - "time complexity", "prove correctness", "recurrence" → `domain="algorithms"`

### 18.2 Problem Representations: `MathProblem` + `DataProblem`

```python
@dataclass
class DataSource:
    kind: str        # "csv", "parquet", "sql", "pandas_df", "simulation"
    location: str    # path, DSN, or name
    description: str

@dataclass
class MathProblem:
    problem_id: str
    raw_query: str
    problem_type: str
    goal: str
    goal_type: str           # "find_value" | "find_expression" | "prove" | "simplify" | "optimize" | "fit_model"
    given: List[MathExpression]
    constraints: List[MathExpression]
    variables: List[str]
    unknowns: List[str]
    domain: Optional[str]    # real | complex | integer | probabilistic | function_space
    context: Optional[str]
    parsed_at: str

@dataclass
class DataProblem(MathProblem):
    """Extension for ML/stats problems that involve data."""
    data_sources: List[DataSource]
    target_variable: Optional[str]
    feature_variables: List[str]
    task_type: Optional[str]      # "regression", "classification", "time_series", "causal", "ab_test"
    metrics: List[str]            # e.g. "MSE", "AUC", "coverage"
    train_test_split: Optional[Dict[str, float]]
```

**ProblemParser** branches:

- If query mentions datasets, CSVs, columns, "regress X on Y", "build a model to predict" → produce `DataProblem`
- If query involves PDEs → produce `MathProblem` with `domain="function_space"` plus PDE metadata (equation type, BCs, geometry)

### 18.3 Planner: SEGO‑style Multi‑Plan DAG

```python
@dataclass
class Subgoal:
    step_id: int
    description: str
    method: str               # "factor_quadratic", "integration_by_parts", "HMC_sampling",
                              # "cross_validation", "mesh_refinement", ...
    input_refs: List[str]     # references into problem/previous step IDs
    expected_output_type: str # "scalar", "expression", "distribution", "model", "field"
    backend_pref: str         # "symbolic" | "numeric" | "optimization" | "stats" | "ml" | "pde" | "sampling" | "formal"
    dependencies: List[int]
    verification_strategy: str
    importance: float         # used in subgoal optimization

@dataclass
class SolutionPlan:
    plan_id: str
    problem: Union[MathProblem, DataProblem]
    approach: str
    primary_backend: str
    subgoals: List[Subgoal]
    estimated_steps: int
    estimated_difficulty: float
    risks: List[str]
    fallback_approaches: List[str]
    world_impact_note: Optional[str]
    search_budget_ms: int                   # used for deep search
    parallelizable_groups: List[List[int]]  # step_ids that can run in parallel
```

**SolutionPlanner** improvements:

- Inspired by SEGO and DELTA‑style task decomposition, treat subgoal selection as **an optimization problem**:
  - Generate multiple candidate subgoal trees
  - Score them using heuristics from benchmarks like MATH, GSM8K, AIME, OlympiadBench
  - Prefer shorter proofs with verifiable steps
- For `DataProblem`:
  - Templates: EDA → candidate model families → cross‑validation plan → diagnostics/robustness checks
- For PDE tasks:
  - Templates: define weak form → choose function space → discretize mesh → solve → refine/check residual

The planner outputs **parallelizable groups**, so the executor can run symbolic and numeric checks concurrently.

---

## 19. Backends: Real Tools, Not Stubs

Each backend exposes a uniform interface:

```python
class Backend(Protocol):
    def can_handle(self, subgoal: Subgoal, problem: MathProblem) -> bool: ...
    def execute(self, subgoal: Subgoal, context: Dict[str, Any]) -> StepResult: ...
```

### 19.1 `SymPyBackend` — Symbolic Computation

```python
class SymPyBackend:
    """Symbolic math via SymPy."""
    
    def solve_equation(self, equation: str, variable: str) -> Dict[str, Any]: ...
    def solve_system(self, equations: List[str], variables: List[str]) -> Dict[str, Any]: ...
    def differentiate(self, expr: str, variable: str, order: int = 1) -> Dict[str, Any]: ...
    def integrate(self, expr: str, variable: str, limits: Optional[Tuple] = None) -> Dict[str, Any]: ...
    def simplify(self, expr: str) -> Dict[str, Any]: ...
    def expand(self, expr: str) -> Dict[str, Any]: ...
    def factor(self, expr: str) -> Dict[str, Any]: ...
    def limit(self, expr: str, variable: str, point: str) -> Dict[str, Any]: ...
    def series(self, expr: str, variable: str, point: str, order: int) -> Dict[str, Any]: ...
    def matrix_ops(self, matrix: List[List], operation: str) -> Dict[str, Any]: ...
```

### 19.2 `NumericBackend` — SciPy/NumPy Numerical Methods

```python
class NumericBackend:
    """Numerical computation via NumPy/SciPy."""
    
    def solve_numeric(self, equation: Callable, initial_guess: float, method: str = "newton") -> Dict: ...
    def optimize(self, objective: Callable, constraints: List[Dict], bounds: List[Tuple], method: str = "SLSQP") -> Dict: ...
    def integrate_numeric(self, func: Callable, a: float, b: float) -> Dict: ...
    def solve_ode(self, func: Callable, y0: List[float], t_span: Tuple, method: str = "RK45") -> Dict: ...
    def solve_linear_system(self, A: np.ndarray, b: np.ndarray) -> Dict: ...
    def eigensolve(self, matrix: np.ndarray) -> Dict: ...
```

### 19.3 `OptimizationBackend` — CVXPY + JAX Optimizers

```python
class OptimizationBackend:
    """Convex & general optimization via CVXPY and JAX."""
    
    def solve_convex(self, objective: str, constraints: List[str], variables: List[str]) -> Dict: ...
    def solve_lp(self, c: np.ndarray, A_ub: np.ndarray, b_ub: np.ndarray) -> Dict: ...
    def solve_qp(self, Q: np.ndarray, c: np.ndarray, constraints: List[Dict]) -> Dict: ...
    def gradient_descent(self, objective: Callable, x0: np.ndarray, lr: float, max_iter: int) -> Dict: ...
    def check_kkt_conditions(self, problem: Dict, solution: Dict) -> Dict: ...
```

### 19.4 `StatsBackend` — statsmodels + scikit-learn

```python
class StatsBackend:
    """Statistics and traditional ML via statsmodels/sklearn."""
    
    def fit_ols(self, X: np.ndarray, y: np.ndarray) -> Dict: ...
    def fit_glm(self, X: np.ndarray, y: np.ndarray, family: str) -> Dict: ...
    def fit_arima(self, series: np.ndarray, order: Tuple[int, int, int]) -> Dict: ...
    def hypothesis_test(self, test_type: str, data: np.ndarray, **kwargs) -> Dict: ...
    def bootstrap_ci(self, data: np.ndarray, statistic: Callable, n_bootstrap: int) -> Dict: ...
    def cross_validate(self, model: Any, X: np.ndarray, y: np.ndarray, cv: int) -> Dict: ...
```

### 19.5 `MLBackend` — PyTorch/JAX for Deep Learning

```python
class MLBackend:
    """Deep learning experiments via PyTorch/JAX."""
    
    def check_gradient(self, func: Callable, analytic_grad: Callable, x: np.ndarray) -> Dict: ...
    def train_small_model(self, model_spec: Dict, data: Dict, epochs: int) -> Dict: ...
    def verify_convergence(self, loss_history: List[float]) -> Dict: ...
    def compare_autodiff_vs_symbolic(self, expr: str, point: np.ndarray) -> Dict: ...
```

### 19.6 `PDEBackend` — FEniCS/Firedrake for Physics

```python
class PDEBackend:
    """PDE solving via FEniCS/Firedrake (optional)."""
    
    def solve_poisson(self, domain: Dict, f: str, bcs: List[Dict]) -> Dict: ...
    def solve_heat_equation(self, domain: Dict, initial: str, bcs: List[Dict], t_final: float) -> Dict: ...
    def solve_navier_stokes(self, domain: Dict, bcs: List[Dict], params: Dict) -> Dict: ...
    def compute_residual_norm(self, solution: Any, pde: Dict) -> Dict: ...
    def mesh_convergence_study(self, pde: Dict, mesh_sizes: List[int]) -> Dict: ...
```

### 19.7 `SamplingBackend` — NumPyro for Bayesian Inference

```python
class SamplingBackend:
    """Bayesian inference via NumPyro HMC/NUTS."""
    
    def sample_posterior(self, model: Callable, data: Dict, num_samples: int) -> Dict: ...
    def compute_credible_interval(self, samples: np.ndarray, alpha: float) -> Dict: ...
    def posterior_predictive(self, model: Callable, samples: Dict, new_data: Dict) -> Dict: ...
    def model_comparison(self, models: List[Callable], data: Dict) -> Dict: ...
```

### 19.8 `LeanBackend` — Formal Theorem Proving (Optional)

```python
class LeanBackend:
    """Formal verification via Lean 4 (optional)."""
    
    def __init__(self, lean_path: Optional[str] = None):
        self.available = self._check_lean_installation()
    
    def formalize_statement(self, statement: str) -> Dict: ...
    def verify_proof(self, lean_code: str) -> Dict: ...
    def search_mathlib(self, query: str) -> Dict: ...
    def generate_proof_sketch(self, statement: str) -> Dict: ...
```

---

## 20. Validator: Multi‑Path, Domain‑Aware

### 20.1 Types

```python
@dataclass
class ValidationCheck:
    check_name: str
    passed: bool
    details: str
    confidence_contribution: float

@dataclass
class ValidationResult:
    valid: bool
    confidence: float
    checks: List[ValidationCheck]
    warnings: List[str]
    suggested_review: bool
    domain: Optional[str]
```

### 20.2 Check Families

**Core Math Checks (for all problems):**

- **Substitution**: Plug answer back into original equation
- **Numerical spot-check**: Evaluate at random test points
- **Alternative-method**: Solve using different backend/approach, compare
- **Bounds/sanity**: Answer in valid range, finite, correct type

**Stats / Probability Checks:**

- Recompute summary statistics and verify reported numbers
- Re‑fit model with different random seeds / splits; check stability
- Hypothesis tests: test statistics match p‑values; residual diagnostics

**ML Checks:**

- Verify shapes, gradient flows, training loss actually decreases
- Train tiny experiments to see if claimed convergence is plausible

**Optimization Checks:**

- Check feasibility (constraints) of claimed solution
- For convex problems: solver status + KKT residuals
- Perturbation test: can objective be improved by small changes?

**Physics/PDE Checks:**

- Residual norm on PDE; check orders of convergence under mesh refinement
- Conservation laws (mass/energy, probability mass, etc.)
- Dimensional analysis

**Formal Proof Checks:**

- If Lean/Coq backend available, attempt formalization
- Type-check result as bonus confidence

### 20.3 Confidence Aggregation

```python
def compute_confidence(checks: List[ValidationCheck], domain: str) -> float:
    """
    Weighted confidence with domain-specific adjustments.
    
    Base weights:
    - substitution: 0.30
    - numerical: 0.25
    - alternative_method: 0.20
    - sanity: 0.10
    - domain_specific: 0.15
    
    Domain adjustments:
    - stats: extra weight to diagnostic checks
    - physics: extra weight to residual/conservation checks
    - ml: extra weight to convergence verification
    """
    # ... implementation
```

---

## 21. Explainer: Research‑Style Output

### 21.1 Enhanced Explanation Structure

```python
@dataclass
class ExplanationStep:
    step_number: int
    action: str
    input_expr: str
    output_expr: str
    justification: str
    latex: str
    code_snippet: Optional[str]  # NEW: actual code that ran

@dataclass
class Explanation:
    problem_summary: str
    approach_overview: str
    steps: List[ExplanationStep]
    final_answer: str
    final_answer_latex: str
    key_insights: List[str]
    common_mistakes: List[str]
    related_concepts: List[str]
    limitations: List[str]           # NEW: what this solution doesn't cover
    reproducibility_notes: List[str] # NEW: seeds, data splits, solver options
    visualizations: List[str]        # NEW: descriptions of plots to generate
```

### 21.2 Domain-Specific Explanations

**For DataProblem (stats/ML):**

- "Data story": what the model is doing, assumptions, diagnostics, and limitations
- Visuals: residual plots, learning curves, calibration curves
- Model card: performance metrics, failure modes, appropriate use cases

**For PDE/Physics:**

- Explanation of the physical model (e.g., Poisson, heat equation)
- Boundary conditions interpretation
- Mesh refinement behavior and convergence analysis

**For Optimization:**

- Dual interpretation when available
- Trade-off analysis (Pareto frontiers, sensitivity)
- Constraint binding analysis

---

## 22. MathModeOrchestrator 3.0

### 22.1 Configuration

```python
@dataclass
class MathModeOptions:
    max_retries: int = 3
    auto_verify: bool = True
    compute_tier: str = "standard"  # "light" | "standard" | "deep_search"
    strict_world_impact: bool = True
    enable_code_execution: bool = True
    max_compute_ms: Optional[int] = None
```

### 22.2 OODA Flow (Refined)

```python
class MathModeOrchestrator:
    def __init__(self):
        self.detector = MathDetector()
        self.parser = ProblemParser()
        self.planner = SolutionPlanner()
        self.executor = MathExecutor()
        self.validator = MathValidator()
        self.explainer = MathExplainer()
        
        # Hooks
        self.on_problem_parsed: Optional[Callable[[MathProblem], bool]] = None
        self.on_plan_ready: Optional[Callable[[SolutionPlan], bool]] = None
        self.on_verification_failed: Optional[Callable[[ValidationResult], str]] = None
    
    def process(self, query: str, synthesis: Optional[Dict] = None,
                options: Optional[MathModeOptions] = None) -> MathModeResult:
        
        options = options or MathModeOptions()
        
        # OBSERVE
        intent = self.detector.detect(query, synthesis)
        if not intent.is_math:
            return self._non_math_fallback(query)
        
        # ORIENT
        problem = self.parser.parse(query, intent)
        if self.on_problem_parsed and not self.on_problem_parsed(problem):
            return self._aborted("Problem parsing rejected by hook")
        
        # ARCHITECT
        plan = self.planner.plan(problem)
        if self.on_plan_ready and not self.on_plan_ready(plan):
            return self._aborted("Plan rejected by hook")
        
        # ACT + VERIFY LOOP
        validation = None
        for iteration in range(1, options.max_retries + 1):
            result = self.executor.execute(plan, options.compute_tier)
            
            if not options.auto_verify:
                break
            
            validation = self.validator.validate(problem, result)
            
            if validation.valid and validation.confidence >= 0.7:
                break
            
            if self.on_verification_failed:
                hint = self.on_verification_failed(validation)
                # Could adjust plan based on hint
            
            # Optionally escalate compute_tier for retry
            if options.compute_tier == "light":
                options.compute_tier = "standard"
        
        # EXPLAIN
        explanation = self.explainer.explain(problem, result)
        
        # RENDER
        color_tiles = self.render_math_tiles(intent, plan, result, validation)
        conversation_response = self.format_response(explanation, validation, color_tiles)
        
        return MathModeResult(
            success=result.success and (validation is None or validation.valid),
            mode_triggered=True,
            intent=intent,
            problem=problem,
            plan=plan,
            result=result,
            validation=validation,
            explanation=explanation,
            iterations=iteration,
            total_time_ms=...,
            conversation_response=conversation_response,
            color_tiles=color_tiles
        )
```

### 22.3 Deep Search Mode

For `compute_tier="deep_search"`:

- Generate multiple **alternative** plans and candidate solutions
- Use self‑consistency voting across solutions
- Apply verification‑guided CoT and forward‑backward reasoning
- This is what you crank up for Olympiad/Putnam/IMO‑style tasks

### 22.4 Ultra Mode Integration

For tasks requiring experiments or generated code:

1. MathMode can emit a **BuildSpec** to Ultra Mode (e.g., "create `pde_solve.py` using FEniCS with these weak forms")
2. Ultra Mode builder executes the spec
3. MathMode uses the resulting scripts via appropriate backend
4. Results flow back for verification

This gives you a **math + builder closed loop**: design → build → run → verify → refine.

---

## 23. Domain Packs

Domain-specific logic lives in `quintet/math/domains/`.

### 23.1 `prob_stats.py` — Probability & Statistics

**Capabilities:**

- Automated EDA: summary stats, correlations, missingness, visual diagnostics
- Model selection: heuristics for linear vs logistic vs Poisson vs mixed models vs time‑series
- Hypothesis tests: t‑tests, chi‑square, ANOVA, non‑parametrics; automatic assumption checking
- Bayesian inference: interfaces to NumPyro with HMC/NUTS

**Validation:**

- Recompute metrics, verify p‑values / CIs
- Check for impossible results (probabilities outside [0,1], negative variances)
- Stability across random seeds

### 23.2 `ml_opt.py` — ML & Optimization

**Capabilities:**

- Quick PyTorch/JAX model definitions and training loops for small experiments
- CVXPY for convex optimization (Lasso, portfolio, resource allocation)
- JAX for gradient checking and high‑order derivatives

**Validation:**

- Re‑run training with different seeds; check trend consistency
- Verify objective can't be improved by small perturbations
- Check duality gaps for convex problems

### 23.3 `physics_pde.py` — Physics & PDEs

**Capabilities:**

- Parse PDE‑style statements ("solve ∂u/∂t = Δu…") into internal PDE spec
- Generate FEniCS/Firedrake or JAX PDE scripts
- Compute solutions, residuals, convergence tables, derived physical quantities

**Validation:**

- Residual norms vs mesh/time refinement
- Conservation laws (mass, energy, probability)
- Dimensional analysis

### 23.4 `algorithms_cs.py` — Algorithms & CS Math

**Capabilities:**

- Recognize complexity, correctness, approximation algorithm queries
- Plan: prove correctness → build implementation via Ultra Mode → run scaling tests
- Reason about recurrences, invariants, worst‑case bounds

**Validation:**

- Empirical vs theoretical complexity on sample sizes
- Property‑based tests for counterexamples

---

## 24. Benchmarks & Evaluation

Wire a benchmark runner in `math/eval/`:

### 24.1 Datasets

- **GSM8K / GSM8K-Platinum** — grade school math
- **MATH** — competition math (Hendrycks et al.)
- **AIME 2024/2025** — American Invitational Math Exam
- **OlympiadBench** — Olympiad-level problems
- **IMO-Bench** — International Math Olympiad problems

### 24.2 Metrics

- **pass@k** — success rate with k attempts
- **Accuracy** — correct final answer
- **Step-level validation rate** — % of steps that verify
- **Calibration** — confidence vs actual correctness
- **Time per problem** — compute efficiency

### 24.3 Modes

- `light` — single CoT plan, minimal verification
- `standard` — full verification stack
- `deep_search` — multi‑plan + multi‑sample + heavy verification

This gives you a concrete way to iterate: see where performance saturates vs test‑time compute and quickly compare architectural tweaks.

---

## 25. Color Tiles (Math 3.0 Aware)

Extend Cool Color Tiles for Math Mode 3.0:

| Position | Name | Color Palette | Signals |
|----------|------|---------------|---------|
| A1 | Detection | Soft blues | Math confidence + domain classification |
| A2 | Problem Type | Soft blues | Type + difficulty level |
| A3 | Compute Tier | Blues → amber | light/standard/deep_search |
| B1 | Parse Quality | Violets | Structure extraction success |
| B2 | Plan Elegance | Violets | Subgoal count, DAG width, parallelization |
| B3 | Backend Selection | Violets | Which backends engaged (sympy/cvxpy/etc) |
| C1 | Execution | Greens/reds | Solve success per backend |
| C2 | Verification | Greens/amber/reds | Multi-path validation confidence |
| C3 | World Impact | Greens/alert | Impact category + conservatism level |

When a **world‑impact category** is involved (climate, healthcare, humanitarian), color the relevant tiles slightly more "alert" unless validation confidence is very high.

The tile JSON is usable by the Deep Researcher UI to show e.g., "physics‑PDE + deep search + high residual confidence + medium world‑impact conservatism".

---

## 26. Implementation Contracts & Schemas

This section locks down the metadata schemas and behavioral contracts that UI, organism relay, and MemoryGraph depend on. **These are stable interfaces—change with care.**

### 26.1 Metadata Schema: `context_flow`

```python
@dataclass
class ContextFlowEntry:
    """Single entry in the context flow log."""
    timestamp: str              # ISO 8601
    phase: str                  # "observe" | "orient" | "architect" | "act" | "verify"
    source: str                 # Directory, file, or component that influenced decision
    target: str                 # What was affected
    influence_type: str         # "dependency" | "pattern" | "constraint" | "heuristic"
    weight: float               # 0.0-1.0, how much this influenced the outcome
    note: Optional[str]         # Human-readable explanation

# Example:
context_flow = [
    ContextFlowEntry(
        timestamp="2025-12-08T14:30:00Z",
        phase="orient",
        source="src/routes/api.py",
        target="blueprint.new_files[0]",
        influence_type="pattern",
        weight=0.8,
        note="Detected FastAPI pattern, biasing toward similar structure"
    ),
    ContextFlowEntry(
        timestamp="2025-12-08T14:30:01Z",
        phase="verify",
        source="MathValidator.substitution_check",
        target="result.confidence",
        influence_type="constraint",
        weight=0.3,
        note="Substitution passed, +0.3 to confidence"
    )
]
```

**Contract**: Both Build Mode and Math Mode MUST emit `context_flow` as a `List[ContextFlowEntry]` in their result objects.

### 26.2 Metadata Schema: `color_tiles`

```python
@dataclass
class ColorTile:
    """Single tile in the 3x3 color grid."""
    tile_id: str                # "A1", "B2", "C3", etc.
    color: str                  # Hex color code
    mood: str                   # "confident" | "uncertain" | "alert" | "satisfied" | "processing"
    signal: str                 # "success" | "warning" | "error" | "waiting"
    tagline: str                # Two-word summary
    value: Optional[float]      # 0.0-1.0 for gradient tiles
    data_reference: str         # JSON path to source data (e.g., "intent.confidence")
    data_snapshot: Optional[Any]  # Actual value for quick inspection
    
    # Machine-readable links for MemoryGraph/Atlas
    memory_embedding_id: Optional[str]  # Link to proof memory embedding
    related_tiles: List[str]    # Other tile_ids this relates to

@dataclass  
class ColorTileGrid:
    """Complete 3x3 tile grid with metadata."""
    grid_id: str                # Unique identifier
    mode: str                   # "build" | "math"
    tiles: List[ColorTile]      # Exactly 9 tiles
    generated_at: str           # ISO 8601
    problem_hash: str           # Hash of input for deduplication
    
    def to_human_readable(self) -> str:
        """Render as ASCII art for logs."""
        ...
    
    def to_json(self) -> Dict:
        """Machine-readable format for MemoryGraph."""
        ...
```

**Contract**: 
- Tiles MUST include `data_reference` pointing to actual result data
- Tiles SHOULD include `memory_embedding_id` when proof memory is available
- Both human-readable (`to_human_readable()`) and machine-readable (`to_json()`) formats MUST be emitted

### 26.3 Metadata Schema: `cognition_summary`

```python
@dataclass
class CognitionSummary:
    """3-sentence summary of what was observed/oriented/changed."""
    observed: str               # What was detected/understood
    oriented: str               # How context shaped the approach  
    acted: str                  # What changed as a result
    key_decision: str           # Single most important choice made
    confidence_rationale: str   # Why confidence is at this level
```

**Contract**: Every `MathModeResult` and `BuildResult` MUST include a `cognition_summary`.

### 26.4 Metadata Schema: `incompleteness_score`

```python
@dataclass
class IncompletenessAssessment:
    """Assessment of solution completeness."""
    score: float                # 0.0 (fully incomplete) to 1.0 (fully complete)
    missing_elements: List[str] # What wasn't addressed
    partial_elements: List[str] # What was partially addressed
    next_steps: List[str]       # Recommended follow-up actions
    auto_approve_allowed: bool  # Whether future builds can auto-approve
    
    @property
    def is_acceptable(self) -> bool:
        return self.score >= 0.7
```

**Contract**: 
- Score < 0.7 → `auto_approve_allowed = False`
- Score < 0.5 → Result MUST include populated `next_steps`
- World-impact problems → threshold raised to 0.8

### 26.5 Metadata Schema: `world_impact_note`

```python
@dataclass
class WorldImpactAssessment:
    """Assessment of real-world impact and associated safeguards."""
    category: Optional[str]     # "healthcare_medicine" | "climate_environment" | etc.
    impact_score: float         # 0.0-1.0
    verification_tier: str      # "standard" | "elevated" | "critical"
    confidence_adjustment: float  # Negative adjustment to confidence (e.g., -0.1)
    required_checks: List[str]  # Validation checks that MUST pass
    disclaimer: Optional[str]   # Required disclaimer text
    logged_to_receipt: bool     # Whether this was logged to organism receipt
```

**Contract**:
- Category detected → `verification_tier` MUST be at least "elevated"
- `impact_score > 0.8` → `verification_tier = "critical"`
- Critical tier → ALL `required_checks` MUST pass or result is rejected

### 26.6 Router Confidence Thresholds

```python
class UltraModeRouter:
    """Routes queries with explicit confidence thresholds."""
    
    # Thresholds
    MATH_MODE_THRESHOLD = 0.6      # Below this, don't trigger Math Mode
    BUILD_MODE_THRESHOLD = 0.5     # Below this, don't trigger Build Mode
    TIE_THRESHOLD = 0.1            # If both within this range, use tie-breaker
    
    def route(self, query: str, synthesis: Optional[Dict] = None) -> Tuple[str, Any]:
        math_intent = self.math_mode.detect(query, synthesis)
        build_intent = self.build_mode.detect(query, synthesis)
        
        math_conf = math_intent.confidence if math_intent.is_math else 0.0
        build_conf = build_intent.confidence if build_intent.is_buildable else 0.0
        
        # Neither passes threshold
        if math_conf < self.MATH_MODE_THRESHOLD and build_conf < self.BUILD_MODE_THRESHOLD:
            return "default", None
        
        # Clear winner
        if math_conf >= self.MATH_MODE_THRESHOLD and math_conf > build_conf + self.TIE_THRESHOLD:
            return "math", math_intent
        
        if build_conf >= self.BUILD_MODE_THRESHOLD and build_conf > math_conf + self.TIE_THRESHOLD:
            return "build", build_intent
        
        # Tie-breaker: check for ambiguous prompts
        return self._resolve_tie(query, math_intent, build_intent, synthesis)
    
    def _resolve_tie(self, query, math_intent, build_intent, synthesis) -> Tuple[str, Any]:
        """Resolve ambiguous prompts. Default to Build Mode for 'create'/'make' verbs."""
        build_verbs = ["create", "make", "build", "generate", "implement", "write"]
        math_verbs = ["solve", "prove", "calculate", "find", "compute", "derive"]
        
        query_lower = query.lower()
        
        # Count verb matches
        build_matches = sum(1 for v in build_verbs if v in query_lower)
        math_matches = sum(1 for v in math_verbs if v in query_lower)
        
        if math_matches > build_matches:
            return "math", math_intent
        elif build_matches > math_matches:
            return "build", build_intent
        else:
            # Default to build for ambiguous "create a calculator" type queries
            return "build", build_intent
```

**Contract**: Build Mode is NOT starved—tie goes to Build Mode unless math verbs dominate.

### 26.7 World-Impact Validator Enforcement

```python
class MathValidator:
    """Validator with enforced world-impact thresholds."""
    
    # Standard thresholds
    STANDARD_CONFIDENCE_THRESHOLD = 0.7
    STANDARD_REQUIRED_CHECKS = ["substitution", "numerical"]
    
    # Elevated thresholds (world-impact detected)
    ELEVATED_CONFIDENCE_THRESHOLD = 0.8
    ELEVATED_REQUIRED_CHECKS = ["substitution", "numerical", "alternative_method", "sanity"]
    
    # Critical thresholds (high world-impact)
    CRITICAL_CONFIDENCE_THRESHOLD = 0.9
    CRITICAL_REQUIRED_CHECKS = ["substitution", "numerical", "alternative_method", "sanity", "bounds"]
    
    def validate(self, problem: MathProblem, result: MathResult, 
                 world_impact: Optional[WorldImpactAssessment] = None) -> ValidationResult:
        
        # Determine tier
        if world_impact and world_impact.verification_tier == "critical":
            threshold = self.CRITICAL_CONFIDENCE_THRESHOLD
            required = self.CRITICAL_REQUIRED_CHECKS
        elif world_impact and world_impact.verification_tier == "elevated":
            threshold = self.ELEVATED_CONFIDENCE_THRESHOLD
            required = self.ELEVATED_REQUIRED_CHECKS
        else:
            threshold = self.STANDARD_CONFIDENCE_THRESHOLD
            required = self.STANDARD_REQUIRED_CHECKS
        
        # Run all checks
        checks = self._run_all_checks(problem, result)
        
        # Enforce required checks
        for check_name in required:
            check = next((c for c in checks if c.check_name == check_name), None)
            if check is None or not check.passed:
                return ValidationResult(
                    valid=False,
                    confidence=0.0,
                    checks=checks,
                    warnings=[f"Required check '{check_name}' failed for {world_impact.verification_tier} tier"],
                    suggested_review=True,
                    domain=problem.domain
                )
        
        # Compute confidence with world-impact adjustment
        confidence = self._compute_confidence(checks)
        if world_impact:
            confidence += world_impact.confidence_adjustment  # Negative adjustment
        
        # Log to receipt if world-impact
        if world_impact:
            self._log_to_receipt(problem, result, checks, world_impact)
        
        return ValidationResult(
            valid=confidence >= threshold,
            confidence=confidence,
            checks=checks,
            warnings=[],
            suggested_review=confidence < threshold + 0.1,
            domain=problem.domain
        )
    
    def _log_to_receipt(self, problem, result, checks, world_impact):
        """Log world-impact validation to organism receipt/HUD."""
        receipt = {
            "type": "world_impact_validation",
            "timestamp": datetime.utcnow().isoformat(),
            "problem_id": problem.problem_id,
            "category": world_impact.category,
            "verification_tier": world_impact.verification_tier,
            "checks_passed": [c.check_name for c in checks if c.passed],
            "checks_failed": [c.check_name for c in checks if not c.passed],
            "confidence": result.confidence,
            "disclaimer": world_impact.disclaimer
        }
        # Emit to organism relay
        self.organism_relay.emit_receipt(receipt)
```

**Contract**: World-impact validation MUST be logged to receipts and surfaced in HUD.

### 26.8 Security & Key Configuration

```python
@dataclass
class BackendConfig:
    """Configuration for external service backends."""
    
    # Wolfram Alpha
    wolfram_api_key: Optional[str] = None
    wolfram_timeout_ms: int = 30000
    
    # Lean 4
    lean_binary_path: Optional[str] = None
    mathlib_path: Optional[str] = None
    lean_timeout_ms: int = 60000
    
    # LLM (for explanation generation, strategy hints)
    llm_provider: Optional[str] = None  # "anthropic" | "openai" | "local"
    llm_api_key: Optional[str] = None
    llm_model: Optional[str] = None
    llm_timeout_ms: int = 30000
    
    # NumPyro/JAX
    jax_platform: str = "cpu"  # "cpu" | "gpu" | "tpu"
    
    # FEniCS/Firedrake
    fenics_available: bool = False
    firedrake_available: bool = False
    
    @classmethod
    def from_env(cls) -> "BackendConfig":
        """Load from environment variables."""
        return cls(
            wolfram_api_key=os.environ.get("WOLFRAM_API_KEY"),
            lean_binary_path=os.environ.get("LEAN_PATH"),
            llm_provider=os.environ.get("LLM_PROVIDER"),
            llm_api_key=os.environ.get("LLM_API_KEY"),
            llm_model=os.environ.get("LLM_MODEL"),
            # ... etc
        )
    
    def validate(self) -> List[str]:
        """Return list of warnings for missing optional configs."""
        warnings = []
        if not self.wolfram_api_key:
            warnings.append("Wolfram Alpha unavailable (no API key)")
        if not self.lean_binary_path:
            warnings.append("Lean 4 unavailable (binary not found)")
        if not self.llm_api_key:
            warnings.append("LLM hints unavailable (no API key)")
        return warnings
```

**Contract**: 
- Keys loaded from environment variables, NEVER hardcoded
- Missing optional backends degrade gracefully with warnings
- Sensitive keys NEVER logged or included in receipts

---

## 27. Proof Memory Embeddings (Cognitive Fingerprints)

> **Genius Addition**: Every verified solve becomes a reusable cognitive fingerprint.

### 27.1 Concept

When Math Mode successfully solves and verifies a problem, it generates a **proof memory embedding**—a compact vector representation of:
- The problem structure
- The solution strategy (which subgoals, which backends)
- The verification path (which checks passed)
- Key lemmas/transformations applied

These embeddings are stored in **MemoryGraph/Atlas** and retrieved for future solves to:
1. **Suggest strategies**: "A similar problem was solved via integration by parts"
2. **Bias the planner**: Increase confidence in approaches that worked before
3. **Retrieve lemmas**: Surface relevant mathematical facts from past proofs
4. **Detect patterns**: Recognize problem families across sessions

### 27.2 Schema

```python
@dataclass
class ProofMemoryEmbedding:
    """Cognitive fingerprint of a verified mathematical solution."""
    
    # Identity
    embedding_id: str           # UUID
    problem_hash: str           # Hash of normalized problem statement
    created_at: str             # ISO 8601
    
    # Problem signature
    problem_type: str           # "algebra", "calculus", "optimization", etc.
    problem_domain: str         # "pure_math", "stats", "physics", etc.
    difficulty: str             # "basic" | "intermediate" | "advanced" | "research"
    key_concepts: List[str]     # ["quadratic", "factoring", "zero_product"]
    
    # Solution signature
    approach: str               # High-level approach taken
    subgoal_sequence: List[str] # Ordered list of subgoal methods
    backends_used: List[str]    # Which backends contributed
    transformations: List[str]  # Key mathematical transformations
    
    # Verification signature
    checks_passed: List[str]    # Which validation checks passed
    confidence: float           # Final confidence score
    world_impact_tier: Optional[str]
    
    # Embedding vector (for similarity search)
    vector: List[float]         # Dense embedding (e.g., 384-dim)
    
    # Retrieval metadata
    retrieval_count: int = 0    # How often this was retrieved
    success_when_retrieved: int = 0  # How often retrieval led to success
    
    def similarity(self, other: "ProofMemoryEmbedding") -> float:
        """Cosine similarity between embeddings."""
        return np.dot(self.vector, other.vector) / (
            np.linalg.norm(self.vector) * np.linalg.norm(other.vector)
        )
```

### 27.3 Embedding Generation

```python
class ProofMemoryEncoder:
    """Generates embeddings from verified solutions."""
    
    def __init__(self, encoder_model: str = "all-MiniLM-L6-v2"):
        from sentence_transformers import SentenceTransformer
        self.encoder = SentenceTransformer(encoder_model)
    
    def encode(self, problem: MathProblem, plan: SolutionPlan, 
               result: MathResult, validation: ValidationResult) -> ProofMemoryEmbedding:
        
        # Build text representation for embedding
        text_repr = self._build_text_representation(problem, plan, result)
        
        # Generate dense vector
        vector = self.encoder.encode(text_repr).tolist()
        
        return ProofMemoryEmbedding(
            embedding_id=str(uuid.uuid4()),
            problem_hash=self._hash_problem(problem),
            created_at=datetime.utcnow().isoformat(),
            problem_type=problem.problem_type,
            problem_domain=problem.domain or "unknown",
            difficulty=self._estimate_difficulty(plan),
            key_concepts=self._extract_concepts(problem, plan),
            approach=plan.approach,
            subgoal_sequence=[sg.method for sg in plan.subgoals],
            backends_used=list(set(sr.backend_used for sr in result.step_results)),
            transformations=self._extract_transformations(plan, result),
            checks_passed=[c.check_name for c in validation.checks if c.passed],
            confidence=validation.confidence,
            world_impact_tier=getattr(validation, 'world_impact_tier', None),
            vector=vector
        )
    
    def _build_text_representation(self, problem, plan, result) -> str:
        """Build semantic text for embedding."""
        parts = [
            f"Problem type: {problem.problem_type}",
            f"Goal: {problem.goal}",
            f"Approach: {plan.approach}",
            f"Methods: {', '.join(sg.method for sg in plan.subgoals)}",
            f"Answer: {result.final_answer}" if result.final_answer else ""
        ]
        return " | ".join(p for p in parts if p)
```

### 27.4 Retrieval & Application

```python
class ProofMemoryStore:
    """MemoryGraph/Atlas storage for proof embeddings."""
    
    def __init__(self, atlas_client):
        self.atlas = atlas_client
        self.collection = "proof_memories"
    
    def store(self, embedding: ProofMemoryEmbedding) -> str:
        """Store embedding in Atlas, return ID."""
        return self.atlas.insert(
            collection=self.collection,
            document={
                **asdict(embedding),
                "_vector": embedding.vector
            }
        )
    
    def retrieve_similar(self, query_embedding: List[float], 
                         k: int = 5, 
                         min_similarity: float = 0.7) -> List[ProofMemoryEmbedding]:
        """Retrieve k most similar proof memories."""
        results = self.atlas.vector_search(
            collection=self.collection,
            vector=query_embedding,
            k=k,
            min_score=min_similarity
        )
        return [ProofMemoryEmbedding(**r) for r in results]
    
    def update_retrieval_stats(self, embedding_id: str, led_to_success: bool):
        """Update retrieval statistics for learning."""
        self.atlas.update(
            collection=self.collection,
            id=embedding_id,
            updates={
                "$inc": {
                    "retrieval_count": 1,
                    "success_when_retrieved": 1 if led_to_success else 0
                }
            }
        )


class MathModeOrchestrator:
    """Orchestrator with proof memory integration."""
    
    def process(self, query: str, ...) -> MathModeResult:
        # ... existing OBSERVE/ORIENT ...
        
        # RETRIEVE: Check proof memory for similar problems
        query_embedding = self.encoder.encode_query(query, intent)
        similar_proofs = self.proof_store.retrieve_similar(query_embedding, k=3)
        
        # BIAS: Use retrieved proofs to inform planning
        if similar_proofs:
            self._apply_proof_memory_hints(similar_proofs, plan)
        
        # ... existing ACT/VERIFY ...
        
        # STORE: If successful, create new proof memory
        if result.success and validation.valid and validation.confidence >= 0.8:
            new_embedding = self.encoder.encode(problem, plan, result, validation)
            embedding_id = self.proof_store.store(new_embedding)
            
            # Link to color tiles
            color_tiles = self.render_math_tiles(...)
            for tile in color_tiles.tiles:
                tile.memory_embedding_id = embedding_id
        
        return MathModeResult(...)
    
    def _apply_proof_memory_hints(self, similar_proofs: List[ProofMemoryEmbedding], 
                                   plan: SolutionPlan):
        """Bias planner based on successful past approaches."""
        # Weight approaches by past success rate
        approach_scores = defaultdict(float)
        for proof in similar_proofs:
            if proof.retrieval_count > 0:
                success_rate = proof.success_when_retrieved / proof.retrieval_count
            else:
                success_rate = 0.5  # Neutral for untested
            approach_scores[proof.approach] += success_rate * proof.confidence
        
        # Suggest best approach
        if approach_scores:
            best_approach = max(approach_scores, key=approach_scores.get)
            plan.suggested_approach = best_approach
            plan.approach_confidence_boost = approach_scores[best_approach] * 0.1
```

### 27.5 Color Tile Integration

Each Math Mode color tile now carries a link to proof memory:

```python
# In tile generation
tile_c2 = ColorTile(
    tile_id="C2",
    color=gradient_green(validation.confidence),
    mood="confident",
    signal="success",
    tagline="Verified Solve",
    value=validation.confidence,
    data_reference="validation.confidence",
    data_snapshot=validation.confidence,
    memory_embedding_id=new_embedding.embedding_id if new_embedding else None,
    related_tiles=["B2", "C1"]  # Plan elegance, execution
)
```

**Result**: Every verified solve becomes a searchable, reusable cognitive fingerprint. Future Math Mode runs can retrieve similar fingerprints to suggest strategies, and the tile grid becomes a visual index into the proof memory corpus.

---

## 28. Math Mode 3.0 Implementation Roadmap (Phased)

> **Key Insight**: Ship tests per phase. Don't move to Phase N+1 until Phase N tests pass.

### Phase 1: Foundation (Week 1-2)
**Gate**: `test_detector.py`, `test_parser.py`, `test_sympy_backend.py` all green
- [ ] Implement `MathDetector` with domain classification
- [ ] Implement `ProblemParser` with `MathProblem` and `DataProblem` types
- [ ] Set up `SymPyBackend` with core operations
- [ ] Set up `NumericBackend` with SciPy integration
- [ ] Basic `MathValidator` with substitution + numerical checks
- [ ] Simple end-to-end test: solve `x^2 - 4 = 0`

### Phase 2: Planner & Executor (Week 3-4)
**Gate**: `test_planner.py`, `test_executor.py`, integration test solves quadratics + derivatives

- [ ] Implement `SolutionPlanner` with SEGO-style subgoal DAGs
- [ ] Implement `MathExecutor` with backend dispatch
- [ ] Add parallelizable group detection in planner
- [ ] Basic `MathValidator` with substitution + numerical checks
- [ ] Test on: multi-step algebra, basic calculus

### Phase 3: Verification & Validation (Week 5-6)
**Gate**: `test_validator.py` with all check types, confidence scoring tests

- [ ] Full `MathValidator` with domain-specific checks
- [ ] Implement confidence scoring with domain-aware aggregation
- [ ] World-impact detection and elevated thresholds
- [ ] Receipt logging for world-impact validations
- [ ] Test on: optimization problems, world-impact scenarios

### Phase 4: Explanation & Metadata (Week 7-8)
**Gate**: `test_explainer.py`, metadata schema compliance tests

- [ ] Implement `MathExplainer` with code snippets and limitations
- [ ] Emit stable metadata: `context_flow`, `color_tiles`, `incompleteness_score`, `cognition_summary`
- [ ] LaTeX output formatting
- [ ] Human-readable + machine-readable color tile output
- [ ] Test on: multi-step proofs, stats problems

### Phase 5: Integration & Router (Week 9-10)
**Gate**: Router tie-breaker tests, `/math/*` API endpoint tests

- [ ] Implement `MathModeOrchestrator` with full OODA loop
- [ ] Router with confidence thresholds and tie-breaker logic
- [ ] HTTP API endpoints (`/math/detect`, `/math/solve`, `/math/verify`)
- [ ] Emit metadata via `/status` endpoint
- [ ] Security/key configuration from environment

### Phase 6: Advanced Backends (Week 11-12)
**Gate**: Optional backends degrade gracefully when unavailable

- [ ] Implement `OptimizationBackend` with CVXPY
- [ ] Implement `StatsBackend` with statsmodels/sklearn
- [ ] Implement `MLBackend` for gradient checking (optional)
- [ ] Implement `SamplingBackend` with NumPyro (optional)
- [ ] Implement `PDEBackend` with FEniCS/Firedrake (optional)
- [ ] Implement `LeanBackend` for formal proofs (optional)
- [ ] Add compute tier support (light/standard/deep_search)

### Phase 7: Proof Memory & Eval (Week 13+)
**Gate**: Proof memory retrieval improves solve rate on held-out problems

- [ ] Implement `ProofMemoryEncoder` and `ProofMemoryStore`
- [ ] Integrate proof memory into planner bias
- [ ] Link color tiles to memory embeddings
- [ ] Set up benchmark harness (MATH, GSM8K, AIME, OlympiadBench)
- [ ] Implement domain packs (`prob_stats.py`, `ml_opt.py`, `physics_pde.py`, `algorithms_cs.py`)
- [ ] Run eval sweeps across compute tiers

---

## 29. Example Math Mode 3.0 Sessions

### Example 1: Algebra (Basic)

**Input**: "Solve x^2 + 5x + 6 = 0"

**Process**:
```
OBSERVE: MathIntent(is_math=True, confidence=0.95, problem_type="algebra", domain="pure_math")
ORIENT:  MathProblem(goal="find x", given=["x^2 + 5x + 6 = 0"])
ARCHITECT: SolutionPlan(approach="factoring", subgoals=[
             1. Factor quadratic
             2. Apply zero product property
             3. Solve each factor
           ], primary_backend="symbolic")
ACT:     SymPyBackend.solve_equation() → x = -2, x = -3
VERIFY:  Substitution check: (-2)^2 + 5(-2) + 6 = 4 - 10 + 6 = 0 ✓
                            (-3)^2 + 5(-3) + 6 = 9 - 15 + 6 = 0 ✓
         Alternative method (quadratic formula): confirmed ✓
         Confidence: 0.98
```

**Output**:
```
## Solution

The equation x² + 5x + 6 = 0 has solutions:

**x = -2** and **x = -3**

### Steps:
1. Factor the quadratic: (x + 2)(x + 3) = 0
2. Apply zero product property: x + 2 = 0 or x + 3 = 0
3. Solve: x = -2 or x = -3

### Verification:
✓ Both solutions satisfy the original equation
✓ Confirmed via quadratic formula
Confidence: 98%
```

### Example 2: Optimization with World Impact (Healthcare)

**Input**: "Find the optimal drug dosage rate to maximize absorption while minimizing toxicity, given absorption A(r) = 100(1 - e^(-0.1r)) and toxicity T(r) = 0.01r^2"

**Process**:
```
OBSERVE: MathIntent(is_math=True, confidence=0.92, problem_type="optimization",
                    domain="pure_math", world_impact_category="healthcare_medicine")
ORIENT:  MathProblem(goal="maximize A(r) - T(r)", 
                     given=[A(r), T(r)], constraints=["r > 0"])
ARCHITECT: SolutionPlan(approach="calculus_optimization", subgoals=[
             1. Define objective function f(r) = A(r) - T(r)
             2. Compute f'(r)
             3. Set f'(r) = 0 and solve
             4. Verify maximum via second derivative test
           ], primary_backend="symbolic", world_impact_note="Healthcare - extra verification")
ACT:     SymPyBackend.differentiate() + solve() → r ≈ 23.03
VERIFY:  Second derivative negative at r=23.03 ✓
         NumericBackend.optimize() confirms ✓
         Bounds check: r > 0 satisfied ✓
         Confidence: 0.94 (conservative due to healthcare impact)
```

**Output**:
```
## Solution: Optimal Drug Dosage Rate

🏥 **World Impact Note**: This optimization problem relates to pharmacokinetics—
finding dosing strategies that maximize therapeutic benefit while minimizing harm.

**Optimal dosage rate: r ≈ 23.03 units/hour**

### Analysis:
1. Objective: Maximize net benefit B(r) = A(r) - T(r)
             = 100(1 - e^(-0.1r)) - 0.01r²

2. First derivative: B'(r) = 10e^(-0.1r) - 0.02r

3. Setting B'(r) = 0: 10e^(-0.1r) = 0.02r
   Numerical solution: r ≈ 23.03

4. Second derivative test: B''(23.03) < 0 → confirmed maximum

### Clinical Interpretation:
- At r = 23.03: Absorption ≈ 90%, Toxicity ≈ 5.3 units
- Net benefit is maximized at this rate

### Verification:
✓ Second derivative confirms maximum
✓ Numerical optimizer agrees
✓ Solution satisfies constraints

⚠️ **Note**: This is a mathematical model. Actual dosing requires clinical validation.

Confidence: 94% (conservative for healthcare applications)
```

### Example 3: Statistics with Data (Regression)

**Input**: "Fit a linear regression to predict house prices from square footage. Data in housing.csv"

**Process**:
```
OBSERVE: MathIntent(is_math=True, confidence=0.88, problem_type="statistics",
                    domain="stats", requires_data=True)
ORIENT:  DataProblem(goal="predict price", task_type="regression",
                     data_sources=[DataSource(kind="csv", location="housing.csv")],
                     target_variable="price", feature_variables=["sqft"],
                     metrics=["R2", "MSE", "residual_diagnostics"])
ARCHITECT: SolutionPlan(approach="ols_regression", subgoals=[
             1. Load and validate data
             2. Exploratory analysis
             3. Fit OLS model
             4. Compute metrics
             5. Diagnostic checks
           ], primary_backend="stats")
ACT:     StatsBackend.fit_ols() → price = 50000 + 150*sqft
VERIFY:  R² = 0.72 (acceptable)
         Residual normality: Shapiro-Wilk p=0.23 ✓
         Homoscedasticity: Breusch-Pagan p=0.15 ✓
         Cross-validation R²: 0.69 ± 0.04 (stable)
         Confidence: 0.85
```

**Output**:
```
## Solution: House Price Prediction Model

### Model:
**price = $50,000 + $150 × sqft**

Interpretation: Each additional square foot adds ~$150 to the predicted price.
Base price (intercept): $50,000

### Performance:
- R² = 0.72 (model explains 72% of price variance)
- RMSE = $45,000
- Cross-validation R² = 0.69 ± 0.04

### Diagnostic Checks:
✓ Residuals approximately normal (Shapiro-Wilk p=0.23)
✓ Homoscedasticity satisfied (Breusch-Pagan p=0.15)
✓ No significant outliers detected

### Limitations:
- Linear model may miss non-linear relationships
- Single predictor; consider adding bedrooms, location, etc.
- Extrapolation beyond data range unreliable

### Reproducibility:
- Random seed: 42
- Train/test split: 80/20
- Statsmodels OLS with HC3 standard errors

Confidence: 85%
```

### Example 4: PDE with Physics (Heat Equation)

**Input**: "Solve the heat equation ∂u/∂t = α∇²u on a unit square with zero boundary conditions and initial temperature u(x,y,0) = sin(πx)sin(πy)"

**Process**:
```
OBSERVE: MathIntent(is_math=True, confidence=0.90, problem_type="differential_equations",
                    domain="physics", requires_code_exec=True)
ORIENT:  MathProblem(goal="find u(x,y,t)", domain="function_space",
                     pde_type="parabolic", boundary_conditions="Dirichlet zero",
                     initial_condition="sin(πx)sin(πy)")
ARCHITECT: SolutionPlan(approach="finite_element", subgoals=[
             1. Define weak form
             2. Create mesh (unit square)
             3. Set up function spaces
             4. Time-step with implicit Euler
             5. Verify against analytical solution
           ], primary_backend="pde")
ACT:     PDEBackend.solve_heat_equation() → u(x,y,t) numerical solution
         Analytical check: u_exact = exp(-2απ²t)sin(πx)sin(πy)
VERIFY:  L2 error vs analytical: 1.2e-4 (mesh h=0.05) ✓
         Mesh convergence: O(h²) confirmed ✓
         Energy decreasing: ✓
         Confidence: 0.91
```

**Output**:
```
## Solution: Heat Equation on Unit Square

### Problem:
∂u/∂t = α∇²u on Ω = [0,1]²
u = 0 on ∂Ω (boundary)
u(x,y,0) = sin(πx)sin(πy) (initial condition)

### Analytical Solution:
u(x,y,t) = exp(-2απ²t) · sin(πx)sin(πy)

The initial temperature distribution decays exponentially with time constant τ = 1/(2απ²).

### Numerical Verification:
- Method: FEniCS finite element, P1 elements, implicit Euler
- Mesh: 40×40 triangular elements (h ≈ 0.035)
- Time step: Δt = 0.001

### Convergence Analysis:
| Mesh size h | L2 error    | Order |
|-------------|-------------|-------|
| 0.10        | 4.8e-3      | -     |
| 0.05        | 1.2e-3      | 2.0   |
| 0.025       | 3.0e-4      | 2.0   |

✓ Confirms O(h²) convergence as expected for P1 elements.

### Physical Interpretation:
- Heat diffuses from center toward boundaries
- Temperature approaches zero as t → ∞
- Decay rate controlled by thermal diffusivity α

Confidence: 91%
```

### Example 5: Proof (Mathematical Induction)

**Input**: "Prove that the sum of the first n positive integers is n(n+1)/2"

**Process**:
```
OBSERVE: MathIntent(is_math=True, confidence=0.88, problem_type="proof",
                    domain="pure_math")
ORIENT:  MathProblem(goal="prove", goal_type="prove",
                     statement="Σ(i=1 to n) i = n(n+1)/2")
ARCHITECT: SolutionPlan(approach="induction", subgoals=[
             1. Base case (n=1)
             2. Inductive hypothesis
             3. Inductive step (n → n+1)
             4. Conclude
           ], primary_backend="symbolic", verification_strategy="numerical_spot_check")
ACT:     Symbolic verification of each step
VERIFY:  Numerical spot-check for n=1,5,10,100 ✓
         Algebraic manipulation verified ✓
         (Optional) Lean formalization available
         Confidence: 0.96
```

**Output**:
```
## Proof by Mathematical Induction

**Theorem**: For all positive integers n, Σᵢ₌₁ⁿ i = n(n+1)/2

### Base Case (n = 1):
- LHS: Σᵢ₌₁¹ i = 1
- RHS: 1(1+1)/2 = 1
- LHS = RHS ✓

### Inductive Hypothesis:
Assume the formula holds for some k ≥ 1:
Σᵢ₌₁ᵏ i = k(k+1)/2

### Inductive Step (prove for k+1):
Σᵢ₌₁ᵏ⁺¹ i = (Σᵢ₌₁ᵏ i) + (k+1)
           = k(k+1)/2 + (k+1)      [by hypothesis]
           = k(k+1)/2 + 2(k+1)/2
           = (k+1)(k+2)/2
           = (k+1)((k+1)+1)/2 ✓

### Conclusion:
By the principle of mathematical induction, the formula holds for all n ≥ 1. ∎

### Verification:
✓ Numerical check: n=100 → 1+2+...+100 = 5050 = 100(101)/2 ✓
✓ Each algebraic step verified symbolically

Confidence: 96%
```

---

## 30. Math Mode 3.0 Testing Strategy

### 28.1 Unit Tests

```python
# tests/math/test_detector.py
def test_detect_algebra():
    detector = MathDetector()
    intent = detector.detect("solve x^2 - 4 = 0")
    assert intent.is_math == True
    assert intent.problem_type == "algebra"
    assert intent.confidence > 0.8
    assert intent.domain == "pure_math"

def test_detect_stats():
    detector = MathDetector()
    intent = detector.detect("fit a regression model to predict sales")
    assert intent.is_math == True
    assert intent.problem_type == "statistics"
    assert intent.requires_data == True
    assert intent.domain == "stats"

def test_detect_pde():
    detector = MathDetector()
    intent = detector.detect("solve the heat equation with Dirichlet boundary conditions")
    assert intent.is_math == True
    assert intent.problem_type == "differential_equations"
    assert intent.domain == "physics"
    assert intent.requires_code_exec == True

def test_detect_non_math():
    detector = MathDetector()
    intent = detector.detect("tell me about the history of mathematics")
    assert intent.is_math == False

# tests/math/test_validator.py
def test_substitution_check():
    validator = MathValidator()
    problem = MathProblem(given=["x^2 - 4 = 0"], unknowns=["x"])
    check = validator._substitution_check(problem, "x = 2")
    assert check.passed == True

def test_numerical_spot_check():
    validator = MathValidator()
    # Verify integral of x^2 from 0 to 1 equals 1/3
    check = validator._numerical_spot_check(
        expr="integrate(x^2, (x, 0, 1))",
        answer="1/3"
    )
    assert check.passed == True
    assert abs(check.numerical_value - 0.333333) < 0.001

# tests/math/test_backends.py
def test_sympy_backend_solve():
    backend = SymPyBackend()
    result = backend.solve_equation("x**2 - 4", "x")
    assert result["success"] == True
    assert set(result["solutions"]) == {-2, 2}

def test_optimization_backend_cvxpy():
    backend = OptimizationBackend()
    result = backend.solve_lp(
        c=np.array([1, 2]),
        A_ub=np.array([[1, 1], [2, 1]]),
        b_ub=np.array([4, 5])
    )
    assert result["success"] == True
    assert result["status"] == "optimal"

def test_stats_backend_ols():
    backend = StatsBackend()
    X = np.array([[1], [2], [3], [4], [5]])
    y = np.array([2, 4, 6, 8, 10])
    result = backend.fit_ols(X, y)
    assert result["success"] == True
    assert abs(result["coefficients"][0] - 2.0) < 0.01  # slope ≈ 2
```

### 28.2 Integration Tests

```python
# tests/math/test_math_mode.py
def test_full_pipeline_algebra():
    orchestrator = create_math_orchestrator()
    result = orchestrator.process("solve 2x + 3 = 7")
    assert result.success == True
    assert "x = 2" in result.explanation.final_answer
    assert result.validation.confidence > 0.9

def test_full_pipeline_calculus():
    orchestrator = create_math_orchestrator()
    result = orchestrator.process("find the derivative of x^3")
    assert result.success == True
    assert "3x^2" in result.explanation.final_answer or "3*x**2" in result.explanation.final_answer

def test_full_pipeline_optimization():
    orchestrator = create_math_orchestrator()
    result = orchestrator.process("minimize x^2 + y^2 subject to x + y = 1")
    assert result.success == True
    assert result.plan.primary_backend in ["optimization", "symbolic"]
    assert result.validation.confidence > 0.8

def test_world_impact_detection():
    orchestrator = create_math_orchestrator()
    result = orchestrator.process(
        "optimize vaccine distribution to minimize deaths"
    )
    assert result.intent.world_impact_category == "healthcare_medicine"
    # Should have stricter verification
    assert result.validation.checks_count > 3

def test_compute_tier_escalation():
    orchestrator = create_math_orchestrator(compute_tier="light")
    # First attempt with light tier
    result = orchestrator.process("prove that sqrt(2) is irrational")
    # If light tier fails, should escalate
    if not result.success:
        orchestrator.options.compute_tier = "standard"
        result = orchestrator.process("prove that sqrt(2) is irrational")
    assert result.success == True
```

### 28.3 Benchmark Suite

Run against standard math benchmarks:

```python
# tests/math/test_benchmarks.py
import pytest
from math.eval.benchmarks import load_benchmark, run_benchmark

@pytest.mark.benchmark
def test_gsm8k_sample():
    """Test on GSM8K sample (grade school math)."""
    problems = load_benchmark("gsm8k", sample_size=100)
    results = run_benchmark(problems, compute_tier="standard")
    assert results.accuracy > 0.85  # Target: 85%+ on GSM8K

@pytest.mark.benchmark
def test_math_sample():
    """Test on MATH benchmark sample."""
    problems = load_benchmark("math", sample_size=50)
    results = run_benchmark(problems, compute_tier="standard")
    assert results.accuracy > 0.50  # Target: 50%+ on MATH

@pytest.mark.benchmark
@pytest.mark.slow
def test_olympiad_sample():
    """Test on OlympiadBench sample (requires deep_search)."""
    problems = load_benchmark("olympiadbench", sample_size=10)
    results = run_benchmark(problems, compute_tier="deep_search")
    # Olympiad problems are hard; measure progress, not perfection
    assert results.accuracy > 0.20
    assert results.partial_credit > 0.40
```

### 28.4 Property-Based Testing

```python
# tests/math/test_properties.py
from hypothesis import given, strategies as st

@given(st.integers(min_value=-100, max_value=100))
def test_linear_equation_always_verifiable(a):
    """Any linear equation solution should verify via substitution."""
    if a == 0:
        return  # Skip degenerate case
    orchestrator = create_math_orchestrator()
    result = orchestrator.process(f"solve {a}x + 5 = 0")
    assert result.validation.checks["substitution"].passed == True

@given(st.floats(min_value=0.1, max_value=10.0))
def test_derivative_chain_rule(k):
    """Derivative verification should always agree with numerical."""
    orchestrator = create_math_orchestrator()
    result = orchestrator.process(f"find the derivative of sin({k}x)")
    assert result.validation.checks["numerical_spot_check"].passed == True
```

### 28.5 Domain-Specific Test Suites

**Stats/ML Tests:**
- Regression coefficient recovery on synthetic data
- Hypothesis test p-value accuracy
- Cross-validation stability across seeds

**PDE Tests:**
- Convergence order verification
- Conservation law satisfaction
- Manufactured solution tests

**Optimization Tests:**
- KKT condition verification
- Dual gap checks for convex problems
- Perturbation sensitivity

---

## 31. Future Directions

Math Mode 3.0 establishes a foundation. Future enhancements may include:

1. **Handwriting/Image Input**: OCR for photographed math problems
2. **Interactive Exploration**: Step-through solving with user guidance
3. **Research Paper Integration**: Connect to arXiv/MathSciNet for theorem lookup
4. **Collaborative Proof Assistance**: Multi-agent proof search
5. **Automated Curriculum**: Generate practice problems based on weaknesses
6. **Formal Verification Pipeline**: Automated Lean/Coq translation for critical results
7. **Multimodal Reasoning**: Combine with vision for geometry diagrams
8. **Real-Time Compute Scaling**: Dynamic compute tier adjustment based on problem difficulty

---

This completes the Math Mode 3.0 specification. The system is designed to be:

- **Research-Grade**: Handles real ML/stats/physics/algorithms problems, not just contest math
- **Verification-First**: Every answer is checked through domain-appropriate methods
- **Compute-Scalable**: From light single-pass to deep multi-plan search
- **World-Impact Aware**: Stricter standards for problems affecting health, climate, etc.
- **Extensible**: Pluggable backends from SymPy to FEniCS to Lean 4

Together with Ultra Mode's builder capabilities, this creates a system that can reason mathematically AND build the tools to verify and explore that reasoning.

---

## 32. Core Contracts & Architectural Refinements

> **Spec Version**: `quintet-ultra-math-v1.0`  
> **Breaking changes require a migration note in this section.**

This section freezes the minimal, versioned core that both Ultra Mode and Math Mode depend on. Everything else is optional sophistication built on top.

### 32.1 Core Type Hierarchy (Shared)

```python
# quintet/core/types.py
"""Shared core types used by ALL modes. DO NOT add mode-specific fields here."""

from dataclasses import dataclass, field
from typing import List, Dict, Optional, Any
from datetime import datetime
from enum import Enum
import uuid

# === SPEC VERSION ===
SPEC_VERSION = "quintet-ultra-math-v1.0"

# === ERROR TAXONOMY ===

class ErrorCode(Enum):
    """Canonical error codes for all modes."""
    # Detection/Parsing
    PARSE_ERROR = "PARSE_ERROR"
    INTENT_UNCLEAR = "INTENT_UNCLEAR"
    
    # Planning
    PLAN_ERROR = "PLAN_ERROR"
    NO_VIABLE_PLAN = "NO_VIABLE_PLAN"
    CONTRADICTION_UNRESOLVED = "CONTRADICTION_UNRESOLVED"
    
    # Execution
    EXECUTION_ERROR = "EXECUTION_ERROR"
    TIMEOUT = "TIMEOUT"
    RESOURCE_LIMIT = "RESOURCE_LIMIT"
    BACKEND_UNAVAILABLE = "BACKEND_UNAVAILABLE"
    ROLLBACK_FAILED = "ROLLBACK_FAILED"
    
    # Validation
    VALIDATION_ERROR = "VALIDATION_ERROR"
    VERIFICATION_FAILED = "VERIFICATION_FAILED"
    LOW_CONFIDENCE = "LOW_CONFIDENCE"
    
    # Safety
    INCOMPLETE_BUT_SAFE = "INCOMPLETE_BUT_SAFE"
    HIGH_IMPACT_LOW_CONFIDENCE = "HIGH_IMPACT_LOW_CONFIDENCE"
    WORLD_IMPACT_BLOCKED = "WORLD_IMPACT_BLOCKED"

@dataclass
class ModeError:
    """Structured error for any mode."""
    code: ErrorCode
    stage: str              # "detect" | "parse" | "plan" | "execute" | "validate" | "explain"
    message: str
    recoverable: bool
    details: Optional[Dict[str, Any]] = None
    suggested_action: Optional[str] = None  # For UI/user
    organism_action: str = "log"  # "log" | "warn" | "block"
    
    def to_dict(self) -> Dict:
        return {
            "code": self.code.value,
            "stage": self.stage,
            "message": self.message,
            "recoverable": self.recoverable,
            "details": self.details,
            "suggested_action": self.suggested_action,
            "organism_action": self.organism_action
        }

# === VALIDATION (SHARED) ===

@dataclass
class ValidationCheck:
    """Single validation check - SHARED by Build and Math."""
    check_name: str
    check_type: str         # "substitution" | "numeric" | "alternative" | "formal" | "sanity" | "constraint"
    passed: bool
    confidence_contribution: float
    details: str
    execution_time_ms: float = 0.0
    method_used: Optional[str] = None
    data: Optional[Dict[str, Any]] = None

@dataclass
class ValidationResult:
    """Complete validation result - SHARED by Build and Math."""
    valid: bool
    confidence: float
    checks: List[ValidationCheck] = field(default_factory=list)
    diversity_score: float = 0.0  # How different were the verification methods?
    warnings: List[str] = field(default_factory=list)
    errors: List[ModeError] = field(default_factory=list)
    suggested_review: bool = False
    
    @property
    def checks_passed(self) -> int:
        return sum(1 for c in self.checks if c.passed)
    
    @property
    def checks_failed(self) -> int:
        return sum(1 for c in self.checks if not c.passed)

# === CONTEXT FLOW (SHARED) ===

@dataclass
class ContextFlowEntry:
    """Single entry in context flow - SHARED by Build and Math."""
    timestamp: str
    phase: str              # "observe" | "orient" | "architect" | "decide" | "act" | "verify"
    source: str
    target: str
    influence_type: str     # "dependency" | "pattern" | "constraint" | "heuristic" | "retrieval"
    weight: float
    note: Optional[str] = None

# === COGNITION SUMMARY (SHARED) ===

@dataclass
class CognitionSummary:
    """3-sentence cognition summary - SHARED by Build and Math."""
    observed: str
    oriented: str
    acted: str
    key_decision: str
    confidence_rationale: str

# === INCOMPLETENESS (SHARED) ===

@dataclass
class IncompletenessAssessment:
    """Incompleteness assessment - SHARED by Build and Math."""
    score: float            # 0.0 (fully incomplete) to 1.0 (fully complete)
    missing_elements: List[str] = field(default_factory=list)
    partial_elements: List[str] = field(default_factory=list)
    next_steps: List[str] = field(default_factory=list)
    auto_approve_allowed: bool = True
    
    def __post_init__(self):
        # Enforce gating rules
        if self.score < 0.7:
            self.auto_approve_allowed = False
        if self.score < 0.5 and not self.next_steps:
            raise ValueError("score < 0.5 requires populated next_steps")

# === WORLD IMPACT (SHARED) ===

@dataclass
class WorldImpactAssessment:
    """World impact assessment - SHARED by Build and Math."""
    category: Optional[str] = None
    impact_score: float = 0.0
    verification_tier: str = "standard"  # "standard" | "elevated" | "critical"
    confidence_adjustment: float = 0.0   # Negative adjustment
    required_checks: List[str] = field(default_factory=list)
    disclaimer: Optional[str] = None
    logged_to_receipt: bool = False
    
    def __post_init__(self):
        # Enforce tier rules
        if self.category and self.verification_tier == "standard":
            self.verification_tier = "elevated"
        if self.impact_score > 0.8:
            self.verification_tier = "critical"

# === COLOR TILES (SHARED) ===

@dataclass
class ColorTile:
    """Single color tile - SHARED by Build and Math."""
    tile_id: str
    color: str
    mood: str
    signal: str
    tagline: str
    value: Optional[float] = None
    data_reference: str = ""
    data_snapshot: Optional[Any] = None
    memory_embedding_id: Optional[str] = None
    related_tiles: List[str] = field(default_factory=list)

@dataclass
class ColorTileGrid:
    """3x3 color tile grid - SHARED by Build and Math."""
    grid_id: str
    mode: str               # "build" | "math"
    spec_version: str = SPEC_VERSION
    tiles: List[ColorTile] = field(default_factory=list)
    generated_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    problem_hash: Optional[str] = None
    
    def to_json(self) -> Dict:
        return {
            "grid_id": self.grid_id,
            "mode": self.mode,
            "spec_version": self.spec_version,
            "tiles": [vars(t) for t in self.tiles],
            "generated_at": self.generated_at
        }
    
    def to_human_readable(self) -> str:
        """ASCII art representation."""
        lines = [f"╔═══════════════════════════════════╗"]
        lines.append(f"║  Color Tiles ({self.mode})  v{self.spec_version}  ║")
        lines.append(f"╠═══════════╦═══════════╦═══════════╣")
        for row in ["A", "B", "C"]:
            row_tiles = [t for t in self.tiles if t.tile_id.startswith(row)]
            row_str = "║"
            for col in ["1", "2", "3"]:
                tile = next((t for t in row_tiles if t.tile_id == f"{row}{col}"), None)
                if tile:
                    row_str += f" {tile.tagline[:9]:^9} ║"
                else:
                    row_str += f" {'???':^9} ║"
            lines.append(row_str)
            if row != "C":
                lines.append(f"╠═══════════╬═══════════╬═══════════╣")
        lines.append(f"╚═══════════╩═══════════╩═══════════╝")
        return "\n".join(lines)

# === BASE RESULT (SHARED) ===

@dataclass
class ModeResultBase:
    """Base result class - inherited by BuildResult and MathModeResult."""
    # Identity
    result_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    spec_version: str = SPEC_VERSION
    mode: str = "unknown"
    
    # Core status
    success: bool = False
    errors: List[ModeError] = field(default_factory=list)
    
    # Shared metadata (stable contracts)
    context_flow: List[ContextFlowEntry] = field(default_factory=list)
    color_tiles: Optional[ColorTileGrid] = None
    cognition_summary: Optional[CognitionSummary] = None
    incompleteness: Optional[IncompletenessAssessment] = None
    world_impact: Optional[WorldImpactAssessment] = None
    
    # Timing
    total_time_ms: float = 0.0
    
    def to_base_dict(self) -> Dict:
        """Serialize base fields."""
        return {
            "result_id": self.result_id,
            "spec_version": self.spec_version,
            "mode": self.mode,
            "success": self.success,
            "errors": [e.to_dict() for e in self.errors],
            "context_flow": [vars(cf) for cf in self.context_flow],
            "color_tiles": self.color_tiles.to_json() if self.color_tiles else None,
            "cognition_summary": vars(self.cognition_summary) if self.cognition_summary else None,
            "incompleteness": vars(self.incompleteness) if self.incompleteness else None,
            "world_impact": vars(self.world_impact) if self.world_impact else None,
            "total_time_ms": self.total_time_ms
        }
```

### 32.2 Canonical JSON Wire Examples

**MathModeResult (Success)**:
```json
{
  "result_id": "550e8400-e29b-41d4-a716-446655440000",
  "spec_version": "quintet-ultra-math-v1.0",
  "mode": "math",
  "success": true,
  "mode_triggered": true,
  "errors": [],
  
  "intent": {
    "is_math": true,
    "confidence": 0.95,
    "problem_type": "algebra",
    "domain": "pure_math",
    "world_impact_category": null,
    "compute_tier": "standard"
  },
  
  "result": {
    "final_answer": "x = 2, x = -2",
    "final_answer_latex": "x = \\pm 2",
    "confidence": 0.98
  },
  
  "validation": {
    "valid": true,
    "confidence": 0.98,
    "diversity_score": 0.67,
    "checks": [
      {"check_name": "substitution", "check_type": "core", "passed": true, "confidence_contribution": 0.3},
      {"check_name": "numerical", "check_type": "core", "passed": true, "confidence_contribution": 0.25},
      {"check_name": "alternative_method", "check_type": "core", "passed": true, "confidence_contribution": 0.25}
    ],
    "warnings": []
  },
  
  "context_flow": [
    {"timestamp": "2025-12-08T14:30:00Z", "phase": "observe", "source": "query", "target": "intent", "influence_type": "pattern", "weight": 0.95, "note": "Clear algebra pattern detected"},
    {"timestamp": "2025-12-08T14:30:01Z", "phase": "verify", "source": "substitution_check", "target": "confidence", "influence_type": "constraint", "weight": 0.3, "note": "Both solutions verified"}
  ],
  
  "color_tiles": {
    "grid_id": "tile-001",
    "mode": "math",
    "spec_version": "quintet-ultra-math-v1.0",
    "tiles": [
      {"tile_id": "A1", "color": "#4CAF50", "mood": "confident", "signal": "success", "tagline": "Clear Math", "value": 0.95, "data_reference": "intent.confidence"},
      {"tile_id": "C2", "color": "#4CAF50", "mood": "confident", "signal": "success", "tagline": "Verified", "value": 0.98, "data_reference": "validation.confidence"}
    ]
  },
  
  "cognition_summary": {
    "observed": "Detected quadratic equation in standard form with clear 'solve' intent.",
    "oriented": "Selected factoring approach as equation has integer roots.",
    "acted": "Factored to (x-2)(x+2)=0, solved for x=±2, verified via substitution.",
    "key_decision": "Used factoring over quadratic formula for cleaner solution.",
    "confidence_rationale": "Three independent verification methods agree: substitution, numerical, and alternative (quadratic formula)."
  },
  
  "incompleteness": {
    "score": 1.0,
    "missing_elements": [],
    "partial_elements": [],
    "next_steps": [],
    "auto_approve_allowed": true
  },
  
  "world_impact": null,
  
  "total_time_ms": 127.5,
  "iterations": 1,
  "conversation_response": "## Solution\n\nThe equation x² - 4 = 0 has solutions:\n\n**x = 2** and **x = -2**\n\n..."
}
```

**MathModeResult (Failure - World Impact)**:
```json
{
  "result_id": "550e8400-e29b-41d4-a716-446655440001",
  "spec_version": "quintet-ultra-math-v1.0",
  "mode": "math",
  "success": false,
  "mode_triggered": true,
  
  "errors": [
    {
      "code": "HIGH_IMPACT_LOW_CONFIDENCE",
      "stage": "validate",
      "message": "Healthcare problem failed elevated verification threshold (0.8)",
      "recoverable": true,
      "details": {"confidence": 0.72, "threshold": 0.8, "tier": "elevated"},
      "suggested_action": "Review solution manually before clinical use",
      "organism_action": "warn"
    }
  ],
  
  "validation": {
    "valid": false,
    "confidence": 0.72,
    "diversity_score": 0.33,
    "checks": [
      {"check_name": "substitution", "passed": true, "confidence_contribution": 0.3},
      {"check_name": "numerical", "passed": true, "confidence_contribution": 0.25},
      {"check_name": "alternative_method", "passed": false, "confidence_contribution": 0.0}
    ],
    "warnings": ["Alternative method check failed - only 2 of 3 methods agree"]
  },
  
  "world_impact": {
    "category": "healthcare_medicine",
    "impact_score": 0.85,
    "verification_tier": "elevated",
    "confidence_adjustment": -0.05,
    "required_checks": ["substitution", "numerical", "alternative_method", "sanity"],
    "disclaimer": "This is a mathematical model. Actual dosing requires clinical validation.",
    "logged_to_receipt": true
  },
  
  "color_tiles": {
    "tiles": [
      {"tile_id": "C2", "color": "#FFA500", "mood": "alert", "signal": "warning", "tagline": "Low Conf", "value": 0.72},
      {"tile_id": "C3", "color": "#FF5722", "mood": "alert", "signal": "warning", "tagline": "HighImpact", "value": 0.85}
    ]
  }
}
```

### 32.3 Error Semantics & Color Tile Mapping

| Error Code | Stage | Color Tile Effect | Organism Action |
|------------|-------|-------------------|-----------------|
| `PARSE_ERROR` | detect/parse | A2 → red | log |
| `INTENT_UNCLEAR` | detect | A1 → amber | log |
| `PLAN_ERROR` | plan | B2 → red | log |
| `NO_VIABLE_PLAN` | plan | B1-B3 → red | warn |
| `CONTRADICTION_UNRESOLVED` | plan | B3 → red, special marker | block until resolved |
| `EXECUTION_ERROR` | execute | C1 → red | warn |
| `TIMEOUT` | execute | C1 → amber | log |
| `VALIDATION_ERROR` | validate | C2 → red | warn |
| `LOW_CONFIDENCE` | validate | C2 → amber | log |
| `HIGH_IMPACT_LOW_CONFIDENCE` | validate | C2+C3 → amber/red | warn, require review |
| `WORLD_IMPACT_BLOCKED` | validate | C3 → red | block |
| `INCOMPLETE_BUT_SAFE` | any | varies | log, show next_steps |

### 32.4 Verification Diversity Score

```python
def compute_diversity_score(checks: List[ValidationCheck]) -> float:
    """
    Compute how diverse the verification methods are.
    High diversity = stronger trust (not just agreeing backends).
    """
    method_categories = {
        "symbolic": {"substitution", "symbolic_simplify", "formal_proof"},
        "numeric": {"numerical", "numerical_spot_check", "monte_carlo"},
        "structural": {"bounds", "sanity", "dimensional_analysis"},
        "alternative": {"alternative_method", "cross_backend"},
    }
    
    categories_used = set()
    for check in checks:
        if check.passed:
            for category, methods in method_categories.items():
                if check.check_type in methods or check.check_name in methods:
                    categories_used.add(category)
    
    # Diversity = fraction of categories covered
    return len(categories_used) / len(method_categories)
```

**Contract**: `diversity_score < 0.5` triggers a warning in `ValidationResult`.

### 32.5 Router Arbitration Rules (Refined)

```python
class UltraModeRouter:
    """Refined router with explicit arbitration rules."""
    
    # Thresholds
    MATH_STRONG_THRESHOLD = 0.75   # Clear math intent
    MATH_WEAK_THRESHOLD = 0.5     # Possible math
    BUILD_STRONG_THRESHOLD = 0.7  # Clear build intent
    BUILD_WEAK_THRESHOLD = 0.4    # Possible build
    
    def route(self, query: str, synthesis: Optional[Dict] = None) -> Tuple[str, Any]:
        math_intent = self.math_detector.detect(query, synthesis)
        build_intent = self.build_detector.detect(query, synthesis)
        
        math_conf = math_intent.confidence if math_intent.is_math else 0.0
        build_conf = build_intent.confidence if build_intent.is_buildable else 0.0
        
        # === RULE 1: Strong math with explicit expressions ===
        if math_conf >= self.MATH_STRONG_THRESHOLD:
            if self._has_explicit_expressions(query):
                return "math", math_intent
        
        # === RULE 2: Strong build with repo context ===
        if build_conf >= self.BUILD_STRONG_THRESHOLD:
            if self._has_repo_context(query):
                return "build", build_intent
        
        # === RULE 3: Clear winner ===
        if math_conf >= self.MATH_WEAK_THRESHOLD and math_conf > build_conf + 0.2:
            return "math", math_intent
        if build_conf >= self.BUILD_WEAK_THRESHOLD and build_conf > math_conf + 0.2:
            return "build", build_intent
        
        # === RULE 4: Ambiguous - use heuristics ===
        if math_conf >= self.MATH_WEAK_THRESHOLD and build_conf >= self.BUILD_WEAK_THRESHOLD:
            return self._resolve_ambiguous(query, math_intent, build_intent)
        
        # === RULE 5: Neither strong enough ===
        return "default", None
    
    def _resolve_ambiguous(self, query: str, math_intent, build_intent) -> Tuple[str, Any]:
        """Resolve ambiguous 'build a math module that computes integrals' type queries."""
        
        # Check for "build/create/implement" + math terms
        query_lower = query.lower()
        
        # Pattern: "build X that does Y" where Y is math
        if re.search(r'\b(build|create|implement|write)\b.*\b(that|which|to)\b', query_lower):
            # This is a BUILD request with math functionality
            return "build", build_intent
        
        # Pattern: explicit math request with implementation context
        if re.search(r'\b(solve|prove|calculate)\b', query_lower) and not re.search(r'\b(module|function|class|file)\b', query_lower):
            return "math", math_intent
        
        # Default: prefer build for compound requests
        return "build", build_intent
    
    def _has_explicit_expressions(self, query: str) -> bool:
        """Check for explicit mathematical expressions."""
        return bool(re.search(r'[a-z]\s*[\+\-\*/\^=]\s*[a-z0-9]|\\frac|\\int|\d+x', query, re.I))
    
    def _has_repo_context(self, query: str) -> bool:
        """Check for repository/code context."""
        return bool(re.search(r'\b(src/|tests/|\.py|\.js|module|package|file|directory)\b', query, re.I))
```

### 32.6 Math Receipts

Math Mode emits these receipts for organism/Guardian integration:

```python
@dataclass
class MathProblemReceipt:
    """Emitted when a math problem is parsed."""
    receipt_type: str = "math_problem"
    timestamp: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    problem_id: str = ""
    intent_confidence: float = 0.0
    problem_type: str = ""
    domain: str = ""
    world_impact_category: Optional[str] = None
    estimated_difficulty: str = ""
    
@dataclass
class MathSolutionReceipt:
    """Emitted when a math problem is solved."""
    receipt_type: str = "math_solution"
    timestamp: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    problem_id: str = ""
    success: bool = False
    final_answer: Optional[str] = None
    confidence: float = 0.0
    diversity_score: float = 0.0
    validation_summary: Dict[str, bool] = field(default_factory=dict)  # check_name -> passed
    iterations: int = 1
    compute_tier_used: str = "standard"
    proof_embedding_id: Optional[str] = None

@dataclass  
class MathFailureReceipt:
    """Emitted when math verification fails."""
    receipt_type: str = "math_failure"
    timestamp: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    problem_id: str = ""
    error_code: str = ""
    failure_stage: str = ""
    failure_reason: str = ""
    checks_passed: List[str] = field(default_factory=list)
    checks_failed: List[str] = field(default_factory=list)
    world_impact_blocked: bool = False
    suggested_remedy: Optional[str] = None
```

**Contract**: All receipts thread into the organism receipt chain via `organism_relay.emit_receipt(receipt)`.

### 32.7 Resource Governance

```python
@dataclass
class ResourceLimits:
    """Resource limits per compute tier."""
    max_wall_time_ms: int
    max_plans: int
    max_solutions_per_plan: int
    max_verification_paths: int
    max_memory_mb: int
    max_shell_runtime_ms: int
    
RESOURCE_LIMITS = {
    "light": ResourceLimits(
        max_wall_time_ms=5000,
        max_plans=1,
        max_solutions_per_plan=1,
        max_verification_paths=2,
        max_memory_mb=256,
        max_shell_runtime_ms=10000
    ),
    "standard": ResourceLimits(
        max_wall_time_ms=30000,
        max_plans=3,
        max_solutions_per_plan=2,
        max_verification_paths=4,
        max_memory_mb=1024,
        max_shell_runtime_ms=60000
    ),
    "deep_search": ResourceLimits(
        max_wall_time_ms=300000,
        max_plans=10,
        max_solutions_per_plan=5,
        max_verification_paths=8,
        max_memory_mb=4096,
        max_shell_runtime_ms=300000
    )
}
```

**Contract**: Exceeding any limit results in `TIMEOUT` or `RESOURCE_LIMIT` error. Heavy math (PDEs, LPs) MUST respect same limits as builder.

### 32.8 Explainer Modes

```python
class ExplainerMode(Enum):
    PEDAGOGICAL = "pedagogical"  # More steps, simpler methods, teaching focus
    EXPERT = "expert"            # Minimal steps, advanced techniques, efficiency focus

@dataclass
class ExplainerConfig:
    mode: ExplainerMode = ExplainerMode.PEDAGOGICAL
    max_steps_shown: int = 10
    include_alternatives: bool = True
    include_common_mistakes: bool = True  # Only in PEDAGOGICAL
    include_efficiency_notes: bool = False  # Only in EXPERT
```

**Contract**: Explainer mode stored in receipts. UI can toggle. Default is PEDAGOGICAL.

### 32.9 Math + Build Cross-Coupling

For composite tasks ("implement a function that solves this ODE and prove it converges"):

```python
@dataclass
class MathBuildTask:
    """Task emitted by Math Mode for Build Mode to execute."""
    task_id: str
    description: str
    required_script: str          # Script path to create
    script_content: str           # Generated code
    expected_outputs: List[str]   # Files/artifacts expected
    test_commands: List[str]      # Commands to verify
    math_problem_id: str          # Link back to originating math problem
    timeout_ms: int = 60000

class MathModeOrchestrator:
    def _emit_build_task(self, task: MathBuildTask) -> BuildResult:
        """Call Build Mode to execute a generated script."""
        blueprint = ProjectBlueprint(
            goal=task.description,
            new_files=[FileSpec(path=task.required_script, content=task.script_content)],
            test_plan=" && ".join(task.test_commands),
            metadata={"math_problem_id": task.math_problem_id}
        )
        return self.build_orchestrator.execute(blueprint.to_json())
```

**Contract**: Math Mode can call Build Mode via `MathBuildTask`. Build Mode results flow back for math verification.

### 32.10 Session-Level Coherence

```python
@dataclass
class MathSession:
    """Per-session state for coherent multi-query math reasoning."""
    session_id: str
    created_at: str
    
    # History
    problems_attempted: List[str] = field(default_factory=list)  # problem_ids
    strategies_tried: Dict[str, List[str]] = field(default_factory=dict)  # problem_id -> strategies
    strategies_discarded: Dict[str, List[str]] = field(default_factory=dict)
    
    # Learned during session
    discovered_lemmas: List[str] = field(default_factory=list)
    useful_patterns: List[str] = field(default_factory=list)
    
    # Aggregated context
    session_context_flow: List[ContextFlowEntry] = field(default_factory=list)
    session_color_tiles: List[ColorTileGrid] = field(default_factory=list)
    
    def add_result(self, result: MathModeResult):
        """Incorporate a result into session state."""
        if result.problem:
            self.problems_attempted.append(result.problem.problem_id)
        if result.plan:
            self.strategies_tried[result.problem.problem_id] = [sg.method for sg in result.plan.subgoals]
        self.session_context_flow.extend(result.context_flow)
        if result.color_tiles:
            self.session_color_tiles.append(result.color_tiles)
```

**Contract**: Sessions are optional. When enabled, `MathSession` is stored in MemoryGraph and retrievable by session_id.

### 32.11 World-Impact Sampling (Anti-Gaming)

```python
class WorldImpactAuditor:
    """Guardian/organism component that samples 'low impact' problems for audit."""
    
    AUDIT_RATE = 0.05  # 5% of low-impact problems get elevated checks
    
    def should_audit(self, result: MathModeResult) -> bool:
        """Randomly audit low-impact problems to catch misclassification."""
        if result.world_impact and result.world_impact.category:
            return False  # Already elevated
        
        # Random sampling
        if random.random() < self.AUDIT_RATE:
            return True
        
        # Heuristic triggers
        if self._contains_impact_keywords(result):
            return True
        
        return False
    
    def _contains_impact_keywords(self, result: MathModeResult) -> bool:
        """Check for hidden impact keywords that weren't detected."""
        keywords = {"drug", "patient", "climate", "safety", "life", "death", "critical"}
        text = result.conversation_response.lower()
        return any(kw in text for kw in keywords)
    
    def audit(self, result: MathModeResult) -> MathModeResult:
        """Re-validate with elevated thresholds."""
        # Re-run validation with elevated tier
        audited_validation = self.validator.validate(
            result.problem, 
            result.result,
            world_impact=WorldImpactAssessment(
                category="audit_sampled",
                verification_tier="elevated"
            )
        )
        result.validation = audited_validation
        return result
```

**Contract**: 5% of "low impact" problems are randomly audited with elevated thresholds to catch misclassification or adversarial prompts.

### 32.12 Proof Atlas Integration

Extending section 27 (Proof Memory Embeddings) into a full **Proof Atlas**:

```python
@dataclass
class ProofAtom:
    """Atomic unit in the Proof Atlas."""
    atom_id: str
    atom_type: str  # "problem" | "lemma" | "theorem" | "pattern" | "strategy"
    
    # Embedding
    embedding: List[float]
    
    # Metadata
    problem_type: Optional[str] = None
    domain: Optional[str] = None
    key_concepts: List[str] = field(default_factory=list)
    
    # For problems/theorems
    statement: Optional[str] = None
    proof_sketch: Optional[str] = None
    
    # For patterns/strategies
    pattern_name: Optional[str] = None
    applicable_to: List[str] = field(default_factory=list)  # problem types
    
    # Validation profile
    verification_methods: List[str] = field(default_factory=list)
    diversity_score: float = 0.0
    confidence: float = 0.0
    world_impact_tags: List[str] = field(default_factory=list)
    
    # Graph edges
    edges: List["ProofEdge"] = field(default_factory=list)

@dataclass
class ProofEdge:
    """Edge in the Proof Atlas graph."""
    edge_type: str  # "used_in" | "generalizes" | "contradicts" | "refines" | "similar_to"
    target_atom_id: str
    weight: float = 1.0
    metadata: Dict[str, Any] = field(default_factory=dict)

class ProofAtlas:
    """Living semantic map of proved structures."""
    
    def __init__(self, memory_graph):
        self.graph = memory_graph
        self.collection = "proof_atlas"
    
    def add_atom(self, atom: ProofAtom) -> str:
        """Add a proof atom to the atlas."""
        return self.graph.insert(self.collection, asdict(atom))
    
    def find_isomorphic(self, problem_embedding: List[float], threshold: float = 0.85) -> List[ProofAtom]:
        """Find problems isomorphic to the query."""
        return self.graph.vector_search(
            self.collection, 
            problem_embedding, 
            k=5, 
            min_score=threshold,
            filter={"atom_type": "problem"}
        )
    
    def get_strategies_for(self, problem_type: str) -> List[ProofAtom]:
        """Get strategies applicable to a problem type."""
        return self.graph.query(
            self.collection,
            filter={"atom_type": "strategy", "applicable_to": {"$contains": problem_type}}
        )
    
    def check_consistency(self, new_atom: ProofAtom) -> List[ProofEdge]:
        """Check if new atom contradicts existing atlas."""
        similar = self.find_isomorphic(new_atom.embedding, threshold=0.7)
        contradictions = []
        for existing in similar:
            if self._is_contradictory(new_atom, existing):
                contradictions.append(ProofEdge(
                    edge_type="contradicts",
                    target_atom_id=existing.atom_id,
                    metadata={"reason": "Conflicting conclusions for similar problem"}
                ))
        return contradictions
```

**Contract**: 
- Every high-confidence Math Mode result creates a `ProofAtom`
- Atoms are linked via edges ("used_in", "generalizes", etc.)
- Future Math Mode runs query the atlas before planning
- Contradictions are surfaced before execution

---

## 33. Build Plan: Implementation Details

This section provides everything needed to actually build Math Mode. It fills gaps in the spec and provides a concrete file-by-file implementation order.

### 32.1 Missing Type Definitions

These types are referenced but not fully defined. Here are the complete definitions:

```python
# quintet/math/types.py
"""Core type definitions for Math Mode."""

from dataclasses import dataclass, field
from typing import List, Dict, Optional, Any, Union
from datetime import datetime
import uuid

# ============================================================
# EXPRESSIONS
# ============================================================

@dataclass
class MathExpression:
    """A mathematical expression with metadata."""
    raw: str                          # Original input string
    normalized: str                   # Standardized form
    sympy_expr: Optional[Any] = None  # Parsed SymPy expression (sympy.Expr)
    latex: Optional[str] = None       # LaTeX representation
    variables: List[str] = field(default_factory=list)
    constants: List[str] = field(default_factory=list)
    operations: List[str] = field(default_factory=list)
    is_equation: bool = False         # Contains '='
    is_inequality: bool = False       # Contains '<', '>', '<=', '>='
    
    @classmethod
    def from_string(cls, s: str) -> "MathExpression":
        """Parse a string into a MathExpression."""
        # Implementation in parser.py
        ...

# ============================================================
# STEP RESULTS
# ============================================================

@dataclass
class StepResult:
    """Result of executing a single subgoal."""
    step_id: int
    subgoal_description: str
    success: bool
    output: Optional[str] = None              # Text representation
    output_expr: Optional[MathExpression] = None  # Structured output
    output_value: Optional[Any] = None        # Numeric value if applicable
    backend_used: str = "unknown"
    method_used: str = "unknown"
    execution_time_ms: float = 0.0
    error_message: Optional[str] = None
    code_executed: Optional[str] = None       # Actual code that ran
    intermediate_steps: List[str] = field(default_factory=list)

# ============================================================
# MATH RESULT
# ============================================================

@dataclass
class MathResult:
    """Complete result from executing a solution plan."""
    result_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    success: bool = False
    final_answer: Optional[str] = None
    final_answer_latex: Optional[str] = None
    final_answer_value: Optional[Any] = None  # Numeric/structured value
    step_results: List[StepResult] = field(default_factory=list)
    total_steps: int = 0
    steps_succeeded: int = 0
    execution_time_ms: float = 0.0
    primary_backend: str = "unknown"
    backends_used: List[str] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    
    @property
    def success_rate(self) -> float:
        if self.total_steps == 0:
            return 0.0
        return self.steps_succeeded / self.total_steps

# ============================================================
# VALIDATION
# ============================================================

@dataclass
class ValidationCheck:
    """Single validation check result."""
    check_name: str                   # "substitution", "numerical", etc.
    check_type: str                   # "core", "domain", "formal"
    passed: bool
    details: str
    confidence_contribution: float    # How much this adds to confidence
    execution_time_ms: float = 0.0
    data: Optional[Dict[str, Any]] = None  # Check-specific data

@dataclass
class ValidationResult:
    """Complete validation result."""
    valid: bool
    confidence: float                 # 0.0 to 1.0
    checks: List[ValidationCheck] = field(default_factory=list)
    checks_passed: int = 0
    checks_failed: int = 0
    warnings: List[str] = field(default_factory=list)
    suggested_review: bool = False
    domain: Optional[str] = None
    world_impact_tier: Optional[str] = None
    
    @property
    def pass_rate(self) -> float:
        total = self.checks_passed + self.checks_failed
        if total == 0:
            return 0.0
        return self.checks_passed / total

# ============================================================
# MATH MODE RESULT (Complete)
# ============================================================

@dataclass
class MathModeResult:
    """Complete result from Math Mode processing."""
    # Core status
    success: bool
    mode_triggered: bool
    
    # Pipeline artifacts
    intent: Optional["MathIntent"] = None
    problem: Optional["MathProblem"] = None
    plan: Optional["SolutionPlan"] = None
    result: Optional[MathResult] = None
    validation: Optional[ValidationResult] = None
    explanation: Optional["Explanation"] = None
    
    # Metadata (stable contracts from section 26)
    context_flow: List["ContextFlowEntry"] = field(default_factory=list)
    color_tiles: Optional["ColorTileGrid"] = None
    cognition_summary: Optional["CognitionSummary"] = None
    incompleteness: Optional["IncompletenessAssessment"] = None
    world_impact: Optional["WorldImpactAssessment"] = None
    
    # Proof memory
    proof_embedding_id: Optional[str] = None
    similar_proofs_retrieved: List[str] = field(default_factory=list)
    
    # Execution metadata
    iterations: int = 1
    total_time_ms: float = 0.0
    compute_tier_used: str = "standard"
    
    # Output
    conversation_response: str = ""
    
    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary for API responses."""
        return {
            "success": self.success,
            "mode_triggered": self.mode_triggered,
            "final_answer": self.result.final_answer if self.result else None,
            "confidence": self.validation.confidence if self.validation else None,
            "iterations": self.iterations,
            "total_time_ms": self.total_time_ms,
            "conversation_response": self.conversation_response,
            "context_flow": [asdict(cf) for cf in self.context_flow],
            "color_tiles": self.color_tiles.to_json() if self.color_tiles else None,
            "cognition_summary": asdict(self.cognition_summary) if self.cognition_summary else None,
        }
```

### 32.2 Detector Keywords & Patterns

Concrete keyword lists for `MathDetector`:

```python
# quintet/math/detector.py (partial)

class MathDetector:
    """Detects math intent from queries."""
    
    # === KEYWORD TAXONOMIES ===
    
    MATH_VERBS = {
        "solve", "calculate", "compute", "find", "determine",
        "prove", "show", "demonstrate", "verify",
        "simplify", "expand", "factor", "reduce",
        "derive", "differentiate", "integrate",
        "evaluate", "estimate", "approximate",
        "minimize", "maximize", "optimize",
        "graph", "plot", "sketch",
    }
    
    BUILD_VERBS = {
        "create", "make", "build", "generate", "implement",
        "write", "develop", "design", "construct",
    }
    
    ANALYSIS_VERBS = {
        "explain", "describe", "tell", "what is", "how does",
        "why", "compare", "contrast", "summarize",
    }
    
    MATH_NOUNS = {
        # Algebra
        "equation", "expression", "polynomial", "quadratic", "linear",
        "variable", "coefficient", "root", "solution", "factor",
        # Calculus
        "derivative", "integral", "limit", "series", "sequence",
        "function", "continuous", "differentiable",
        # Linear Algebra
        "matrix", "vector", "eigenvalue", "eigenvector", "determinant",
        "rank", "null space", "transpose", "inverse",
        # Probability/Stats
        "probability", "distribution", "mean", "variance", "standard deviation",
        "hypothesis", "p-value", "confidence interval", "regression",
        # Geometry
        "angle", "triangle", "circle", "polygon", "area", "volume",
        "perimeter", "diameter", "radius",
        # Number Theory
        "prime", "factorial", "gcd", "lcm", "modular", "divisible",
    }
    
    DOMAIN_KEYWORDS = {
        "stats": {"regression", "p-value", "hypothesis", "confidence", "ANOVA", 
                  "correlation", "variance", "mean", "median", "distribution",
                  "sample", "population", "estimate", "fit"},
        "ml": {"train", "model", "gradient", "loss", "optimize", "neural",
               "classifier", "accuracy", "epoch", "batch", "learning rate"},
        "physics": {"force", "energy", "momentum", "velocity", "acceleration",
                    "wave", "field", "potential", "quantum", "relativity",
                    "Navier-Stokes", "Poisson", "Laplace", "heat equation"},
        "algorithms": {"complexity", "O(n)", "runtime", "space", "sort",
                       "search", "graph", "tree", "dynamic programming"},
    }
    
    WORLD_IMPACT_KEYWORDS = {
        "healthcare_medicine": {"drug", "dosage", "patient", "treatment", 
                                "disease", "clinical", "medical", "health"},
        "climate_environment": {"climate", "carbon", "emission", "pollution",
                                "renewable", "energy", "sustainability"},
        "humanitarian_logistics": {"distribute", "allocate", "relief", "aid",
                                   "disaster", "resource", "supply chain"},
    }
    
    # === REGEX PATTERNS ===
    
    EQUATION_PATTERN = re.compile(
        r'[a-zA-Z]\s*[\+\-\*/\^]\s*[a-zA-Z0-9]|'  # x + y, a*b
        r'[a-zA-Z]\s*=\s*[a-zA-Z0-9]|'             # x = 5
        r'\d+[a-zA-Z]|'                            # 2x, 3y
        r'[a-zA-Z]\^[0-9]|'                        # x^2
        r'\\frac|\\sqrt|\\int|\\sum'               # LaTeX
    )
    
    NUMERIC_PATTERN = re.compile(r'\b\d+\.?\d*\b')
    
    FUNCTION_PATTERN = re.compile(
        r'\b(sin|cos|tan|log|ln|exp|sqrt)\s*\(|'
        r'f\s*\(\s*[a-zA-Z]\s*\)|'                 # f(x)
        r'[a-zA-Z]\s*\(\s*[a-zA-Z]\s*\)'           # g(t)
    )
```

### 32.3 File Structure with Dependencies

```
quintet/
├── __init__.py
├── math/
│   ├── __init__.py           # Exports public API
│   ├── types.py              # [NO DEPS] Core dataclasses
│   ├── detector.py           # [DEPS: types] MathDetector, MathIntent
│   ├── parser.py             # [DEPS: types, sympy] ProblemParser
│   ├── planner.py            # [DEPS: types] SolutionPlanner
│   ├── executor.py           # [DEPS: types, backends/*] MathExecutor
│   ├── validator.py          # [DEPS: types, sympy] MathValidator
│   ├── explainer.py          # [DEPS: types] MathExplainer
│   ├── math_mode.py          # [DEPS: all above] MathModeOrchestrator
│   ├── router.py             # [DEPS: math_mode, builder] UltraModeRouter
│   ├── config.py             # [NO DEPS] BackendConfig, env loading
│   ├── metadata.py           # [DEPS: types] Metadata schemas
│   ├── backends/
│   │   ├── __init__.py
│   │   ├── base.py           # [NO DEPS] Backend Protocol
│   │   ├── sympy_backend.py  # [DEPS: base, sympy]
│   │   ├── numeric_backend.py # [DEPS: base, numpy, scipy]
│   │   ├── optimization_backend.py  # [DEPS: base, cvxpy] (Phase 6)
│   │   └── ...
│   ├── domains/              # (Phase 7)
│   ├── memory/               # (Phase 7)
│   │   ├── __init__.py
│   │   ├── encoder.py        # ProofMemoryEncoder
│   │   └── store.py          # ProofMemoryStore
│   └── eval/                 # (Phase 7)
│       ├── __init__.py
│       ├── benchmarks.py
│       └── runners.py
├── builder/                  # Existing Ultra Mode
│   └── ...
└── tests/
    └── math/
        ├── __init__.py
        ├── test_types.py
        ├── test_detector.py
        ├── test_parser.py
        ├── test_planner.py
        ├── test_executor.py
        ├── test_validator.py
        ├── test_math_mode.py
        ├── test_router.py
        └── fixtures/
            ├── algebra_problems.json
            ├── calculus_problems.json
            └── expected_results.json
```

### 32.4 Build Order: Dependency Graph

```
                    ┌─────────────────────────────────────────┐
                    │           PHASE 1: Foundation           │
                    └─────────────────────────────────────────┘
                                      │
         ┌────────────────────────────┼────────────────────────────┐
         ▼                            ▼                            ▼
    ┌─────────┐                 ┌───────────┐                ┌──────────┐
    │ types.py│                 │ config.py │                │ base.py  │
    │ (NO DEP)│                 │ (NO DEP)  │                │ (NO DEP) │
    └────┬────┘                 └─────┬─────┘                └────┬─────┘
         │                            │                           │
         └────────────────────────────┼───────────────────────────┘
                                      │
                    ┌─────────────────────────────────────────┐
                    │         PHASE 2: Core Pipeline          │
                    └─────────────────────────────────────────┘
                                      │
         ┌────────────────────────────┼────────────────────────────┐
         ▼                            ▼                            ▼
    ┌───────────┐              ┌────────────┐              ┌──────────────┐
    │detector.py│              │ parser.py  │              │sympy_backend │
    │DEPS:types │              │DEPS:types, │              │DEPS:base,    │
    └─────┬─────┘              │    sympy   │              │    sympy     │
          │                    └──────┬─────┘              └──────┬───────┘
          │                           │                           │
          └───────────────────────────┼───────────────────────────┘
                                      │
                    ┌─────────────────────────────────────────┐
                    │        PHASE 3: Planning & Exec         │
                    └─────────────────────────────────────────┘
                                      │
                    ┌─────────────────┼─────────────────┐
                    ▼                 ▼                 ▼
              ┌───────────┐    ┌────────────┐    ┌──────────────┐
              │planner.py │    │executor.py │    │numeric_backend│
              │DEPS:types │    │DEPS:types, │    │DEPS:base,    │
              └─────┬─────┘    │  backends  │    │numpy,scipy   │
                    │          └──────┬─────┘    └──────┬───────┘
                    │                 │                 │
                    └─────────────────┼─────────────────┘
                                      │
                    ┌─────────────────────────────────────────┐
                    │       PHASE 4: Validation & Explain     │
                    └─────────────────────────────────────────┘
                                      │
                    ┌─────────────────┼─────────────────┐
                    ▼                 ▼                 ▼
              ┌────────────┐   ┌────────────┐   ┌────────────┐
              │validator.py│   │explainer.py│   │metadata.py │
              │DEPS:types, │   │DEPS:types  │   │DEPS:types  │
              │   sympy    │   └──────┬─────┘   └──────┬─────┘
              └──────┬─────┘          │                │
                     │                │                │
                     └────────────────┼────────────────┘
                                      │
                    ┌─────────────────────────────────────────┐
                    │       PHASE 5: Orchestration            │
                    └─────────────────────────────────────────┘
                                      │
                    ┌─────────────────┼─────────────────┐
                    ▼                 ▼                 ▼
              ┌────────────┐   ┌────────────┐   ┌────────────┐
              │math_mode.py│   │ router.py  │   │  api.py    │
              │DEPS: all   │   │DEPS:math,  │   │DEPS:router │
              │   above    │   │   builder  │   │            │
              └────────────┘   └────────────┘   └────────────┘
                                      │
                    ┌─────────────────────────────────────────┐
                    │       PHASE 6+: Advanced                │
                    └─────────────────────────────────────────┘
                    │ optimization_backend, stats_backend,    │
                    │ domains/*, memory/*, eval/*             │
                    └─────────────────────────────────────────┘
```

### 32.5 File-by-File Implementation Order

**Day 1: Foundation (can parallelize)**
```
1. quintet/math/types.py          # All dataclasses
2. quintet/math/config.py         # BackendConfig
3. quintet/math/backends/base.py  # Backend Protocol
4. tests/math/test_types.py       # Type tests
```

**Day 2: Detection & Parsing**
```
5. quintet/math/detector.py       # MathDetector with keywords
6. tests/math/test_detector.py    # Detection tests
7. quintet/math/parser.py         # ProblemParser
8. tests/math/test_parser.py      # Parser tests
```

**Day 3: Backend & Execution**
```
9.  quintet/math/backends/sympy_backend.py   # SymPy wrapper
10. tests/math/test_sympy_backend.py
11. quintet/math/backends/numeric_backend.py  # NumPy/SciPy wrapper
12. quintet/math/planner.py                   # SolutionPlanner
13. quintet/math/executor.py                  # MathExecutor
14. tests/math/test_executor.py
```

**Day 4: Validation & Explanation**
```
15. quintet/math/validator.py     # MathValidator
16. tests/math/test_validator.py
17. quintet/math/explainer.py     # MathExplainer
18. quintet/math/metadata.py      # Metadata schemas
```

**Day 5: Orchestration & Integration**
```
19. quintet/math/math_mode.py     # MathModeOrchestrator
20. tests/math/test_math_mode.py  # Integration tests
21. quintet/math/router.py        # UltraModeRouter
22. tests/math/test_router.py
```

**Day 6+: API & Polish**
```
23. quintet/math/api.py           # HTTP endpoints
24. Integration with builder/api.py
25. End-to-end tests
```

### 32.6 Test Fixtures

```json
// tests/math/fixtures/algebra_problems.json
{
  "problems": [
    {
      "id": "alg_001",
      "query": "Solve x^2 - 4 = 0",
      "expected_type": "algebra",
      "expected_answers": ["x = 2", "x = -2"],
      "difficulty": "basic"
    },
    {
      "id": "alg_002", 
      "query": "Solve x^2 + 5x + 6 = 0",
      "expected_type": "algebra",
      "expected_answers": ["x = -2", "x = -3"],
      "difficulty": "basic"
    },
    {
      "id": "alg_003",
      "query": "Solve the system: 2x + y = 5, x - y = 1",
      "expected_type": "algebra",
      "expected_answers": ["x = 2", "y = 1"],
      "difficulty": "intermediate"
    }
  ]
}

// tests/math/fixtures/calculus_problems.json
{
  "problems": [
    {
      "id": "calc_001",
      "query": "Find the derivative of x^3",
      "expected_type": "calculus",
      "expected_answers": ["3x^2", "3*x**2"],
      "difficulty": "basic"
    },
    {
      "id": "calc_002",
      "query": "Integrate x^2 from 0 to 1",
      "expected_type": "calculus",
      "expected_answers": ["1/3", "0.333"],
      "difficulty": "basic"
    }
  ]
}
```

### 32.7 requirements.txt

```
# quintet/requirements.txt

# === CORE (Required) ===
sympy>=1.12
numpy>=1.24
scipy>=1.11
matplotlib>=3.7

# === TESTING ===
pytest>=7.4
pytest-cov>=4.1
hypothesis>=6.82  # Property-based testing

# === OPTIONAL: Optimization ===
cvxpy>=1.4

# === OPTIONAL: Stats/ML ===
scikit-learn>=1.3
statsmodels>=0.14

# === OPTIONAL: Deep Learning ===
# torch>=2.0
# jax>=0.4
# jaxlib>=0.4

# === OPTIONAL: Bayesian ===
# numpyro>=0.13

# === OPTIONAL: Proof Memory ===
# sentence-transformers>=2.2  # For embeddings

# === API ===
fastapi>=0.100
pydantic>=2.0
uvicorn>=0.23
```

### 32.8 Minimum Viable Pipeline (MVP)

The absolute minimum to prove the system works:

```python
# MVP: Solve "x^2 - 4 = 0" end-to-end

# 1. Detector
intent = MathDetector().detect("solve x^2 - 4 = 0")
assert intent.is_math == True
assert intent.problem_type == "algebra"

# 2. Parser
problem = ProblemParser().parse("solve x^2 - 4 = 0", intent)
assert problem.goal_type == "find_value"
assert "x" in problem.unknowns

# 3. Planner
plan = SolutionPlanner().plan(problem)
assert len(plan.subgoals) >= 1
assert plan.primary_backend == "symbolic"

# 4. Executor + Backend
result = MathExecutor().execute(plan)
assert result.success == True
assert "2" in result.final_answer or "-2" in result.final_answer

# 5. Validator
validation = MathValidator().validate(problem, result)
assert validation.valid == True
assert validation.confidence >= 0.9

# 6. Orchestrator (all together)
orchestrator = MathModeOrchestrator()
final = orchestrator.process("solve x^2 - 4 = 0")
assert final.success == True
assert final.validation.confidence >= 0.9
```

### 32.9 Success Criteria per Phase

| Phase | Deliverable | Test Gate | Success Metric |
|-------|-------------|-----------|----------------|
| 1 | types.py, config.py, base.py | Types instantiate, serialize | 100% type tests pass |
| 2 | detector.py, parser.py | Detect algebra/calculus/stats | >90% accuracy on 20 test queries |
| 3 | planner.py, executor.py, backends | MVP pipeline works | Solves x^2-4=0 correctly |
| 4 | validator.py, explainer.py | Substitution check passes | Confidence correlates with correctness |
| 5 | math_mode.py, router.py | Full orchestration | 10 algebra + 5 calculus problems pass |
| 6 | Advanced backends | Optional backends work when available | CVXPY solves LP problems |
| 7 | Memory, benchmarks | Proof memory retrieval | GSM8K >85%, memory improves +5% |

---

## 34. Recommended Next Moves

### Today: Scaffold & MVP

**Step 1**: Create directory structure (5 min)
```bash
cd /Users/tim/loom  # or your project root
mkdir -p quintet/math/backends quintet/math/domains quintet/math/memory quintet/math/eval
mkdir -p tests/math/fixtures

# Create all files
touch quintet/__init__.py
touch quintet/math/__init__.py
touch quintet/math/{types,config,detector,parser,planner,executor,validator,explainer,math_mode,router,metadata}.py
touch quintet/math/backends/{__init__,base,sympy_backend,numeric_backend}.py
touch tests/math/{__init__,test_types,test_detector,test_parser,test_executor,test_validator,test_math_mode}.py
```

**Step 2**: Copy types from section 32.1 into `types.py` (10 min)

**Step 3**: Implement MVP detector (30 min)
- Copy keyword lists from section 32.2
- Implement `detect()` method
- Write 5 test cases

**Step 4**: Implement MVP parser (30 min)
- Use SymPy's `parse_expr` for equation extraction
- Handle "solve X = Y" pattern
- Write 5 test cases

**Step 5**: Implement MVP executor + SymPy backend (45 min)
- Wrap `sympy.solve()` for equations
- Handle single-variable polynomials
- Write 3 test cases

**Step 6**: Implement MVP validator (30 min)
- Substitution check only
- Write 3 test cases

**Step 7**: Wire MVP orchestrator (30 min)
- Connect detector → parser → planner → executor → validator
- Test with "solve x^2 - 4 = 0"

**Total MVP time**: ~3 hours

### This Week: Core Pipeline

| Day | Focus | Deliverables |
|-----|-------|--------------|
| Mon | Types + Config + Detector | `types.py`, `config.py`, `detector.py` + tests |
| Tue | Parser + SymPy Backend | `parser.py`, `sympy_backend.py` + tests |
| Wed | Planner + Executor | `planner.py`, `executor.py` + tests |
| Thu | Validator + Explainer | `validator.py`, `explainer.py` + tests |
| Fri | Orchestrator + Integration | `math_mode.py`, integration tests |

### Next Week: Metadata & Router

| Day | Focus | Deliverables |
|-----|-------|--------------|
| Mon | Metadata schemas | `metadata.py` with all contracts from section 26 |
| Tue | Color tiles | Tile generation + JSON/human-readable output |
| Wed | Router | `router.py` with confidence thresholds |
| Thu | API endpoints | `/math/detect`, `/math/solve`, `/math/verify` |
| Fri | Integration tests | End-to-end tests, fix edge cases |

### Week 3+: Advanced Features

- World-impact detection & elevated validation
- Additional backends (CVXPY, statsmodels)
- Proof memory embeddings
- Benchmark harness

### Success Metrics

| Milestone | Metric | Target | When |
|-----------|--------|--------|------|
| MVP | Solves x^2-4=0 | Pass | Day 1 |
| Core | 10 algebra problems | >90% | Week 1 |
| Router | Tie-breaker tests | Pass | Week 2 |
| Metadata | Schema compliance | 100% | Week 2 |
| Benchmarks | GSM8K sample | >85% | Week 4 |

---

## 35. Quick Reference: Key Files & Sections

| Need | File | Section |
|------|------|---------|
| Type definitions | `types.py` | 32.1 |
| Keyword lists | `detector.py` | 32.2 |
| File structure | - | 32.3 |
| Build order | - | 32.4, 32.5 |
| Test fixtures | `fixtures/*.json` | 32.6 |
| Dependencies | `requirements.txt` | 32.7 |
| MVP code | - | 32.8 |
| Success criteria | - | 32.9 |
| Metadata schemas | `metadata.py` | 26.1-26.5 |
| Router thresholds | `router.py` | 26.6 |
| Validator enforcement | `validator.py` | 26.7 |
| Config/keys | `config.py` | 26.8 |
| Proof memory | `memory/*.py` | 27 |

---

*This document is the canonical spec for Quintet + Ultra Mode + Math Mode 3.0. Section 32 provides everything needed to start building. Follow the dependency graph (32.4) and file order (32.5) for a clean implementation path.*
