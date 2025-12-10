# Quintet Security Threat Model

**Version:** 1.0
**Date:** 2024-12-09
**Scope:** Quintet Multi-Mode AI Orchestrator (quintet-ultra-math-v1.1)

---

## 1. System Overview

Quintet is a multi-mode AI orchestrator with two primary execution modes:

- **Build Mode**: Executes project blueprints (creates files, runs shell commands)
- **Math Mode**: Symbolic mathematics using SymPy (parsing expressions, solving equations)

Supporting infrastructure includes:
- Constitutional enforcement (runtime invariant checking)
- Policy receipts and experiment tracking
- Self-healing and stress management

---

## 2. Assets (What We Protect)

| Asset | Description | Sensitivity |
|-------|-------------|-------------|
| **System Availability** | Ability to process queries without crashing/hanging | **High** |
| **Mathematical Correctness** | Accuracy of computed results | **High** |
| **Host Filesystem** | Files outside designated project directories | **Critical** |
| **Host System** | CPU/memory resources, running processes | **High** |
| **Audit Trail Integrity** | Receipts, logs, constitutional check results | **Medium** |
| **User Data** | Input queries, intermediate results | **Low** (no PII expected) |

### Sensitivity Ratings Explained

- **Critical**: Compromise would allow host system takeover
- **High**: Compromise would cause service outage or incorrect outputs
- **Medium**: Compromise affects trust/audit capabilities
- **Low**: Limited impact, recoverable

---

## 3. Threat Actors

### 3.1 Expected User Profile

Based on codebase analysis, Quintet is designed for:

| Actor Type | Trust Level | Description |
|------------|-------------|-------------|
| **Internal developers** | Trusted | Running locally during development |
| **CI/CD pipelines** | Trusted | Automated testing environments |
| **Research users** | Semi-trusted | Running mathematical experiments |

### 3.2 NOT in Scope (Current Design)

The current implementation does **not** appear designed for:
- Public-facing API endpoints
- Multi-tenant environments
- Untrusted external users
- Adversarial attack scenarios

**Key Finding**: This is primarily an internal/research tool, not a production service.

---

## 4. Attack Vectors Analysis

### 4.1 Input Manipulation

| Vector | Description | Likelihood | Impact | Risk |
|--------|-------------|------------|--------|------|
| **Malformed math expressions** | Invalid input to SymPy parser | High | Low | **Low** |
| **Expression complexity bombs** | Expressions designed to hang solver | Medium | High | **High** |
| **Path traversal in file specs** | `../../../etc/passwd` in BuilderExecutor | Low | Critical | **Medium** |
| **Shell injection** | Malicious commands in ShellCommand | Low | Critical | **Medium** |

### 4.2 Resource Exhaustion

| Vector | Description | Likelihood | Impact | Risk |
|--------|-------------|------------|--------|------|
| **Infinite loops in solver** | SymPy hanging on pathological input | Medium | High | **High** |
| **Memory bombs** | Large symbolic expressions | Medium | High | **High** |
| **Shell command timeouts** | Long-running commands | Low | Medium | **Low** |

### 4.3 Policy/Constitutional Bypass

| Vector | Description | Likelihood | Impact | Risk |
|--------|-------------|------------|--------|------|
| **Predicate errors caught as pass** | Exception handling returns True | Low | Medium | **Low** |
| **Invariant disable** | Setting `enabled=False` | Low | Medium | **Low** |
| **Timestamp manipulation** | Fake audit timestamps | Low | Low | **Low** |

### 4.4 Arbitrary Code Execution

| Vector | Description | Likelihood | Impact | Risk |
|--------|-------------|------------|--------|------|
| **SymPy sympify()** | `sympify` with `evaluate=True` on untrusted input | Medium | Critical | **Critical** |
| **subprocess.run(shell=True)** | BuilderExecutor runs shell commands | Medium | Critical | **Critical** |

---

## 5. Risk Assessment Summary

### Risk Matrix

```
Impact
Critical |  [sympify ACE]     |                    |  [shell injection] |
         |  [shell=True ACE]  |                    |  [path traversal]  |
High     |                    | [solver timeout]   |                    |
         |                    | [memory bombs]     |                    |
Medium   |                    | [policy bypass]    |                    |
Low      |                    | [malformed input]  |                    |
         +--------------------|--------------------|--------------------|
                 High              Medium                Low
                               Likelihood
```

### Prioritized Risk List

1. **CRITICAL: SymPy sympify() arbitrary code execution**
   - Location: `quintet/math/parser.py`, `quintet/math/backends/sympy_backend.py`
   - `sympy.sympify(user_input)` can execute arbitrary Python
   - Even with "trusted" users, this is a latent vulnerability

2. **CRITICAL: Shell command execution with shell=True**
   - Location: `quintet/builder/executor.py:226`
   - `subprocess.run(cmd.command, shell=True, ...)` 
   - Direct shell injection if command comes from untrusted source

3. **HIGH: Resource exhaustion (solver timeouts)**
   - Location: `quintet/math/executor.py`, `quintet/math/backends/sympy_backend.py`
   - No timeout on SymPy operations
   - Pathological inputs can hang indefinitely

4. **MEDIUM: Path traversal in BuilderExecutor**
   - Location: `quintet/builder/executor.py:112`
   - No validation that file paths stay within project_root

5. **LOW: Constitutional predicate error handling**
   - Location: `quintet/core/constitutional.py:122-124`
   - Currently returns `(False, error_msg)` on exception - this is correct

---

## 6. Prioritized Fixes Based on Threat Model

Given that this is an **internal/development tool** (not public-facing), I prioritize:

### Must Fix (Critical Risk + Reasonable Effort)

| Priority | Vulnerability | Fix | Effort |
|----------|--------------|-----|--------|
| **P1** | SymPy sympify ACE | Add input sanitization layer | Medium |
| **P2** | Resource limits (timeouts) | Add timeouts to SymPy operations | Low |
| **P3** | Path traversal | Validate paths stay within project_root | Low |

### Should Fix (High Risk)

| Priority | Vulnerability | Fix | Effort |
|----------|--------------|-----|--------|
| **P4** | Shell command injection | Sanitize/validate commands | Medium |

### Won't Fix (This Phase)

| Vulnerability | Reason |
|--------------|--------|
| Full sandboxing | Internal tool, overkill for current use case |
| Encrypted audit trails | No sensitive data being logged |
| Multi-tenant isolation | Not a multi-tenant system |
| Rate limiting | No API exposure |

---

## 7. Security Assumptions

1. **Users are semi-trusted** - They have legitimate access to the system
2. **Inputs may be malformed** - But not actively malicious (bugs, not attacks)
3. **Host system is protected** - Running in dev environments with other safeguards
4. **No external network exposure** - Tool runs locally, not as a service

---

## 8. Recommendations

### Immediate (This PR)

1. Add input sanitization for math expressions
2. Add timeouts to SymPy solve operations
3. Add path validation for BuilderExecutor

### Future Considerations

If Quintet is ever exposed to untrusted users:
- Replace `shell=True` with explicit command arrays
- Add proper sandboxing (containers, seccomp)
- Implement rate limiting
- Add cryptographic signing to receipts

---

## Document History

| Version | Date | Changes |
|---------|------|---------|
| 1.0 | 2024-12-09 | Initial threat model |
