# Project Brain: Puppetlabs / Quintet

This is the central knowledge base for Claude Code. It's loaded automatically at the start of every session.

## Project Overview

This workspace contains diverse projects spanning:
- **Machine Learning** - Training pipelines, model optimization, experiment tracking
- **AI Agents** - Multi-agent systems, tool use, orchestration
- **User Interfaces** - React/Vue/Svelte frontends, component libraries
- **Game Development** - Game loops, physics, ECS architectures
- **Quintet** - The current active project in this repo

## Directory Structure

```
puppetlabs/
├── quintet/           # Active Python project
│   └── ...
├── config/            # Configuration files
├── docs/              # Documentation
├── tests/             # Test suite
├── scripts/           # Utility scripts
├── .claude/           # Claude Code configuration
│   ├── settings.json  # Permissions, hooks, env
│   ├── commands/      # Slash commands (/review, /ship, etc.)
│   ├── agents/        # Subagents (code-reviewer, test-harness, etc.)
│   └── skills/        # Domain expertise (ML, AI agents, UI, games)
└── CLAUDE.md          # This file
```

## Key Commands

### Development
```bash
# Python environment
uv venv && source .venv/bin/activate
uv pip install -e ".[dev]"

# Run tests
pytest tests/ -v

# Format code
python -m black . && python -m isort .

# Type check
python -m mypy . --ignore-missing-imports
```

### Claude Code Rituals
- `/review` - Code review current changes
- `/ship` - Full quality check + prepare commit
- `/surgery <target>` - Careful refactoring with validation
- `/tests <target>` - Design and implement tests
- `/architect <feature>` - Design system architecture
- `/debug <issue>` - Systematic debugging
- `/explain <code>` - Deep dive explanation

## Coding Standards

### Python
- **Formatting**: Black (line length 88) + isort
- **Type hints**: Required for all public functions
- **Docstrings**: Google style for public APIs
- **Testing**: pytest, aim for >80% coverage on core logic

### TypeScript/JavaScript
- **Formatting**: Prettier
- **Linting**: ESLint with strict config
- **Types**: Strict TypeScript, no `any`

### General
- Prefer explicit over implicit
- Keep functions small and focused
- Write tests for non-trivial logic
- Document *why*, not *what*

## Invariants (Never Break These)

1. **Tests must pass** - Never merge code that breaks tests
2. **Type safety** - No untyped public interfaces
3. **No secrets in code** - Use environment variables
4. **Backwards compatibility** - Don't break existing APIs without migration path

## Working with Me

### I Work Best When You:
- Give clear, specific tasks
- Provide context about *why* (not just *what*)
- Let me use subagents for specialized work
- Use slash commands for standard workflows
- Review my suggestions before committing

### I'll Proactively:
- Run code review after significant changes
- Suggest tests for new code
- Format code after edits
- Warn about security issues
- Track tasks with the todo list

## Context Management

If sessions get slow or context feels heavy:
1. Use `/context` to check token usage
2. Consider starting a fresh session
3. Let subagents handle exploratory searches
4. Break large tasks into smaller pieces

## Project-Specific Notes

### Quintet
- Python 3.11+ required
- Uses modern Python features (dataclasses, type hints, match statements)
- See `quintet/` for source code
- See `tests/` for test patterns

---

*Last updated: Session start*
*This file is version controlled and shared across sessions*
