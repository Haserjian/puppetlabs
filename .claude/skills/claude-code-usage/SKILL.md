---
name: claude-code-best-practices
description: Best practices for using Claude Code effectively. Use when the user asks about Claude Code features, configuration, or optimal usage patterns.
---

# Claude Code Best Practices Skill

## Core Philosophy
Claude Code is a **dev exoskeleton**, not just a smart REPL. Use it as an orchestration layer that:
- Enforces quality gates through hooks
- Maintains project knowledge through Skills and CLAUDE.md
- Delegates specialized work to subagents
- Runs named rituals through slash commands

## Optimal Usage Patterns

### 1. Use Slash Commands for Rituals
Don't type ad-hoc prompts for repeated tasks. Define commands:
- `/review` - Code review workflow
- `/ship` - Lint, test, build, commit
- `/surgery` - Careful refactoring with validation

### 2. Let Hooks Enforce Quality
Quality gates belong in hooks, not prompts:
- `PostToolUse` - Format after edits
- `PreToolUse` - Block dangerous commands
- Keep hooks fast (< 5 seconds)

### 3. Use Skills for Domain Knowledge
Skills are for reusable expertise:
- Loaded dynamically when relevant
- Reduce context bloat vs. stuffing everything in prompts
- Version control with your project

### 4. Delegate to Subagents
Don't do everything in one context:
- `code-reviewer` - Focused review, no edits
- `test-harness` - Test-focused reasoning
- `refactorer` - Structure changes only

### 5. Keep CLAUDE.md Focused
Project brain should contain:
- Architecture overview
- Key commands
- Coding standards
- Important invariants
- NOT: Generic advice (put in Skills)

## Context Management
- Use `/context` to visualize token usage
- Keep MCP server count low (3-5 max)
- Prefer concise tool outputs
- Let subagents handle exploratory work

## Security Mindset
- Deny dangerous patterns in settings
- Don't auto-approve everything
- Review MCP servers before adding
- Use sandbox mode for untrusted code

## Performance Tips
- Parallel tool calls when independent
- Background long-running commands
- Use Explore subagent for codebase searches
- Cache expensive computations in files

## When Stuck
1. Check `/context` for token pressure
2. Try a fresh session
3. Break task into smaller pieces
4. Use a specialized subagent
5. Add relevant context to CLAUDE.md
