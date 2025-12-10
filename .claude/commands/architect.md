---
argument-hint: <feature-or-system-to-design>
description: Design system architecture for a new feature or component
allowed-tools: Read, Grep, Glob, Bash, WebSearch, WebFetch, Task
---

# Architecture Design Workflow

Design the architecture for: $ARGUMENTS

## Process

### 1. Gather Requirements
First, ask me clarifying questions about:
- What problem are we solving?
- Who are the users?
- What are the performance requirements?
- What constraints exist (tech stack, timeline, team)?

### 2. Explore Existing System
```bash
# Understand current structure
tree -L 2 -I 'node_modules|__pycache__|.git|venv'

# Find related code
grep -r "related_term" --include="*.py" --include="*.ts" -l
```

### 3. Research (if needed)
Use web search to:
- Find best practices for similar systems
- Evaluate technology options
- Learn from others' architectures

### 4. Present Options
Use the architect agent to design multiple approaches, each with:
- Description
- Pros and cons
- Complexity estimate
- Risk assessment

### 5. Recommend
Based on requirements and constraints, recommend ONE approach with clear justification.

### 6. Create Implementation Plan
Break down into:
- Phase 1: Foundation (lowest risk, must-have)
- Phase 2: Core features
- Phase 3: Enhancements

Each phase should have:
- Specific tasks
- Dependencies
- Acceptance criteria

## Output
Provide a design document I can reference during implementation, including:
- Context and requirements
- Chosen architecture with justification
- Component diagram (ASCII is fine)
- Implementation roadmap
- Risks and mitigations
