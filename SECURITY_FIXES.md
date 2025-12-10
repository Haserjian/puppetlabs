# Security Fixes - Phase 2

**Date:** 2024-12-09
**Scope:** Targeted security hardening based on threat model

---

## Summary

Based on the threat model analysis (see `SECURITY_THREAT_MODEL.md`), we implemented
focused fixes for the top 3 vulnerabilities that apply to Quintet's use case as an
internal/research tool.

| Fix | Vulnerability | Risk Level | Status |
|-----|--------------|------------|--------|
| P1: Math Expression Sanitization | SymPy sympify() ACE | Critical | Done |
| P2: Resource Limits (Timeouts) | Solver hangs | High | Done |
| P3: Path Validation | Path traversal | Medium | Done |

---

## Fix Details

### P1: Math Expression Sanitization

**File:** `/Users/timmybhaserjian/puppetlabs/quintet/security/input_sanitizer.py`

**Problem:** 
`sympy.sympify()` can execute arbitrary Python code when given malicious input.
Even with trusted users, this is a latent vulnerability.

**Solution:**
Added `sanitize_math_expression()` that:
1. Blocks dangerous patterns (dunder methods, eval/exec, import statements, etc.)
2. Detects code injection attempts before they reach sympify
3. Logs suspicious patterns for audit

**Blocked Patterns:**
- `__import__`, `__builtins__`, `__class__`, etc. (dunder access)
- `eval()`, `exec()`, `compile()`, `open()`
- `import`, `from...import`
- `os.`, `sys.`, `subprocess`, `shutil`
- `lambda:`, `def`
- SymPy-specific injection vectors

**Test Coverage:** 18 tests
- Tests for each blocked pattern
- Edge cases (empty, None, unicode, long expressions)
- Safe expression pass-through

**Usage:**
```python
from quintet.security import sanitize_math_expression, is_safe_math_expression

# Full check with details
result = sanitize_math_expression(user_input)
if not result.safe:
    print(f"Blocked: {result.blocked_patterns}")

# Quick boolean check
if is_safe_math_expression(user_input):
    expr = sympy.sympify(user_input)
```

---

### P2: Resource Limits (Timeouts)

**File:** `/Users/timmybhaserjian/puppetlabs/quintet/security/input_sanitizer.py`

**Problem:**
SymPy operations can hang indefinitely on pathological inputs (complexity bombs).
No timeout protection existed.

**Solution:**
Added timeout utilities:
1. `run_with_timeout(func, args, timeout_seconds)` - Wrap any function
2. `@with_timeout(seconds)` - Decorator for timeout protection
3. `TimeoutError` - Custom exception for timeout handling

**Implementation:**
- Uses `signal.SIGALRM` on Unix systems
- Graceful fallback on Windows (no timeout, but no crash)
- Configurable timeout duration

**Test Coverage:** 7 tests
- Fast function success
- Slow function timeout
- Exception handling
- Decorator usage

**Usage:**
```python
from quintet.security import run_with_timeout, with_timeout, TimeoutError

# Wrapper style
success, result, error = run_with_timeout(
    sympy.solve,
    args=(expression, variable),
    timeout_seconds=30.0,
    default=None
)

# Decorator style
@with_timeout(30.0)
def my_solver(expr):
    return sympy.solve(expr)
```

---

### P3: Path Validation

**File:** `/Users/timmybhaserjian/puppetlabs/quintet/security/input_sanitizer.py`

**Problem:**
`BuilderExecutor` creates files based on user-provided paths. Without validation,
paths like `../../../etc/passwd` could escape the project directory.

**Solution:**
Added `validate_path_within_root()` that:
1. Resolves paths (handles `..`, symlinks)
2. Validates path stays within project root
3. Optionally blocks absolute paths

**Test Coverage:** 10 tests
- Valid paths pass
- `../` traversal blocked
- Absolute paths blocked (by default)
- Edge cases (spaces, dots in filenames)

**Usage:**
```python
from quintet.security import validate_path_within_root, validate_file_path

# Full check with details
result = validate_path_within_root(user_path, project_root)
if not result.valid:
    print(f"Blocked: {result.error}")

# Quick boolean check
if validate_file_path(user_path, project_root):
    # Safe to use
    pass
```

---

## Not Implemented (By Design)

Based on the threat model, these were explicitly deprioritized:

| Item | Reason |
|------|--------|
| Full sandboxing | Internal tool, overkill for current use case |
| Shell command sanitization | Would break legitimate build commands |
| Encrypted audit trails | No sensitive data being logged |
| Rate limiting | No API exposure |
| Multi-tenant isolation | Not a multi-tenant system |

---

## Integration Guide

### For Math Mode

The security module should be integrated at the entry points:

```python
# In quintet/math/parser.py or quintet/math/backends/sympy_backend.py

from quintet.security import sanitize_math_expression, run_with_timeout

def safe_sympify(expr: str) -> Any:
    # Step 1: Sanitize
    result = sanitize_math_expression(expr)
    if not result.safe:
        raise ValueError(f"Unsafe expression: {result.blocked_patterns}")
    
    # Step 2: Parse with timeout
    success, parsed, error = run_with_timeout(
        sympy.sympify,
        args=(result.sanitized_input,),
        timeout_seconds=30.0
    )
    if not success:
        raise TimeoutError(error)
    
    return parsed
```

### For Build Mode

```python
# In quintet/builder/executor.py

from quintet.security import validate_path_within_root

def _execute_file_op(self, file_spec: FileSpec) -> FileResult:
    # Validate path before any operation
    validation = validate_path_within_root(file_spec.path, self.project_root)
    if not validation.valid:
        return FileResult(
            path=file_spec.path,
            action=file_spec.action,
            success=False,
            error=f"Path validation failed: {validation.error}"
        )
    
    # Use validated resolved path
    path = validation.resolved_path
    # ... rest of implementation
```

---

## Test Summary

Total new tests: **44**
All original tests: **249** (still passing)
Total tests: **293+**

```
tests/test_security.py::TestMathExpressionSanitization ... 18 tests
tests/test_security.py::TestPathValidation ............. 10 tests
tests/test_security.py::TestTimeouts ................... 7 tests
tests/test_security.py::TestSecurityIntegration ........ 3 tests
tests/test_security.py::TestEdgeCases .................. 6 tests
```

---

## Files Changed

| File | Change |
|------|--------|
| `quintet/security/__init__.py` | New - module exports |
| `quintet/security/input_sanitizer.py` | New - all security utilities |
| `tests/test_security.py` | New - 44 security tests |
| `SECURITY_THREAT_MODEL.md` | New - threat analysis document |
| `SECURITY_FIXES.md` | New - this document |

---

## Next Steps

If Quintet's use case expands to external users:

1. **Integrate security checks** at the actual entry points (parser, executor)
2. **Replace shell=True** with explicit command arrays in BuilderExecutor
3. **Add rate limiting** if exposed as an API
4. **Consider containerization** for full isolation

For now, the security utilities are available and tested, ready for integration.
