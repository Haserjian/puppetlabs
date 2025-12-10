---
description: Safe deploy ritual - lint, test, build, and prepare commit
allowed-tools: Read, Grep, Glob, Bash, Edit, Task
---

# Ship Workflow

Prepare code for deployment with a full quality check pipeline.

## Steps

1. **Check Status**
   ```bash
   git status
   git diff --stat
   ```

2. **Run Quality Checks**

   For Python projects:
   ```bash
   # Format
   python -m black . --check || python -m black .
   python -m isort . --check || python -m isort .

   # Lint
   python -m ruff check . || python -m flake8 .

   # Type check
   python -m mypy . --ignore-missing-imports || true

   # Tests
   python -m pytest tests/ -v
   ```

   For JavaScript/TypeScript projects:
   ```bash
   # Lint & format
   npm run lint || npx eslint . --fix
   npm run format || npx prettier --write .

   # Type check (if TypeScript)
   npx tsc --noEmit || true

   # Tests
   npm test
   ```

3. **Build Check**
   ```bash
   # Python
   python -m build || pip install -e . || true

   # JavaScript
   npm run build || true
   ```

4. **Summarize Results**
   - List any failing checks
   - Summarize the changes being shipped
   - Identify any risks or concerns
   - Suggest a commit message

5. **Ask Before Committing**
   Only commit if all critical checks pass and I confirm.

## Important
- Stop immediately if tests fail
- Warn about any type errors or lint issues
- Don't auto-commit without my approval
