---
argument-hint: <file-or-module-to-test>
description: Design and implement tests for specified code
allowed-tools: Read, Grep, Glob, Bash, Edit, Write, Task
---

# Test Design Workflow

Design and implement tests for: $ARGUMENTS

## Process

### 1. Analyze Target Code
- Read the code thoroughly
- Identify:
  - Public interfaces to test
  - Branching logic (if/else, match/switch)
  - Error handling paths
  - External dependencies to mock
  - Edge cases (empty, null, max, min)

### 2. Check Existing Tests
```bash
# Find existing test files
find . -name "*test*.py" -o -name "*.test.ts" -o -name "*.spec.ts" | head -20

# Check coverage if available
pytest --cov=$ARGUMENTS --cov-report=term-missing || true
```

### 3. Design Test Cases
Present a test plan:

**Unit Tests**
- Happy path: normal operation
- Edge cases: boundary conditions
- Error cases: invalid inputs, failures

**Integration Tests** (if applicable)
- Component interactions
- Database operations
- API calls

### 4. Implement Tests
Use the test-harness agent to implement the tests following project conventions.

Match existing test style:
```bash
# See how other tests are written
head -50 tests/*.py || head -50 **/*.test.ts
```

### 5. Verify Tests
```bash
# Run new tests
pytest tests/test_new.py -v  # or specific test file
npm test -- --testPathPattern="new"

# Ensure they actually test something (mutation testing mindset)
# - Tests should fail if you break the code
# - Tests should pass with correct implementation
```

## Test Quality Checklist
- [ ] Tests have clear, descriptive names
- [ ] Each test focuses on one thing
- [ ] Tests are independent (no shared state)
- [ ] Tests run fast
- [ ] Tests don't depend on external services (mock them)
- [ ] Edge cases are covered
- [ ] Error paths are tested
