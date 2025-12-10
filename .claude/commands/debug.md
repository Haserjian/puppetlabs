---
argument-hint: <error-message-or-symptom>
description: Systematic debugging workflow for tracking down issues
allowed-tools: Read, Grep, Glob, Bash, Edit, Task
---

# Debug Workflow

Investigate and fix: $ARGUMENTS

## Systematic Debugging Process

### 1. Reproduce the Issue
```bash
# Run the failing command/test
# Capture exact error message and stack trace
```

### 2. Gather Information
- Full error message and stack trace
- What changed recently?
  ```bash
  git log --oneline -10
  git diff HEAD~5
  ```
- Environment details (Python version, Node version, OS)

### 3. Form Hypotheses
Based on the error, list possible causes:
1. Hypothesis A: ...
2. Hypothesis B: ...
3. Hypothesis C: ...

### 4. Test Hypotheses (Fastest First)
For each hypothesis:
- What would confirm/deny it?
- Run the simplest test first
- Add debug logging if needed:
  ```python
  import logging
  logging.basicConfig(level=logging.DEBUG)
  ```

### 5. Isolate the Problem
- Binary search through code/commits if needed
  ```bash
  git bisect start
  git bisect bad HEAD
  git bisect good <known-good-commit>
  ```
- Minimal reproduction case

### 6. Fix and Verify
- Make the minimal fix
- Verify the original issue is resolved
- Check for regressions:
  ```bash
  pytest tests/ -v  # or npm test
  ```

### 7. Prevent Recurrence
- Add a test that would have caught this
- Document if it's a tricky issue
- Consider if there are similar bugs elsewhere

## Debug Tools
```bash
# Python
python -m pdb script.py          # Debugger
python -c "import module; print(module.__file__)"  # Find module location
pip show package                  # Package info

# General
which command                     # Find binary location
env | grep RELEVANT              # Check environment
```

## Common Issues Checklist
- [ ] Import/module not found → Check PYTHONPATH, virtualenv
- [ ] Type error → Check function signatures, data types
- [ ] Attribute error → Check object initialization
- [ ] Connection error → Check network, credentials, URLs
- [ ] Permission error → Check file permissions, user context
