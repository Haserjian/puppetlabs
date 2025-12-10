---
argument-hint: <file-or-function-to-refactor>
description: Careful surgical refactoring with validation at each step
allowed-tools: Read, Grep, Glob, Bash, Edit, Task
---

# Surgery Workflow

Perform careful, validated refactoring on: $ARGUMENTS

## Surgical Protocol

### 1. Pre-Op Assessment
- Read and understand the target code completely
- Identify all callers/dependencies:
  ```bash
  grep -r "function_name\|ClassName" --include="*.py" --include="*.ts" --include="*.js"
  ```
- Check existing test coverage
- Document current behavior

### 2. Surgical Plan
Before making ANY changes, present:
- What will change
- Why it's safe
- What tests will verify correctness
- Rollback strategy (we're using git)

### 3. Incremental Execution
For each change:
1. Make ONE small change
2. Run tests immediately:
   ```bash
   pytest tests/ -x -v  # or npm test
   ```
3. If tests fail, STOP and assess
4. If tests pass, continue to next change

### 4. Post-Op Verification
- All tests pass
- No new lint/type errors
- Behavior unchanged (same inputs → same outputs)
- Code is cleaner/simpler

## Safety Rules
- NEVER make multiple changes before testing
- NEVER change behavior (that's a feature, not refactoring)
- ALWAYS have a way to verify correctness
- STOP if anything unexpected happens

## If No Tests Exist
1. First, write tests for current behavior
2. Verify tests pass
3. THEN proceed with surgery
4. Tests should still pass after

Ask me before proceeding if there's any uncertainty about what should change.
