---
description: Trigger a comprehensive code review of recent changes
allowed-tools: Read, Grep, Glob, Bash, Task
---

# Code Review Workflow

Use the code-reviewer subagent to review the current changes.

## Steps

1. First, show me what's changed:
   ```bash
   git status
   git diff --stat
   ```

2. Then use the code-reviewer agent to perform a thorough review of all staged and unstaged changes.

3. Focus the review on:
   - Correctness and logic errors
   - Security vulnerabilities
   - Performance issues
   - Code style and maintainability
   - Missing tests or edge cases

4. Provide a structured review with:
   - **Critical** issues that must be fixed
   - **Warnings** that should be addressed
   - **Suggestions** for improvement
   - **Positive** patterns worth keeping

Be thorough but respect my time - prioritize the most important issues.
