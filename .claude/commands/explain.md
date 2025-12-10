---
argument-hint: <file-or-concept-to-explain>
description: Deep dive explanation of code or concepts
allowed-tools: Read, Grep, Glob, Bash
---

# Explain Workflow

Provide a thorough explanation of: $ARGUMENTS

## Process

### 1. Read and Understand
- Read the target code/file completely
- Trace the execution flow
- Identify key components and their relationships

### 2. Provide Layered Explanation

**High-Level Overview**
- What is the purpose?
- How does it fit in the larger system?
- What problem does it solve?

**Component Breakdown**
For each major component:
- What it does
- How it does it
- Why it's designed this way

**Code Walkthrough**
Walk through the code section by section:
- Entry points
- Main logic flow
- Important functions/classes
- Edge case handling

**Key Concepts**
Explain any non-obvious:
- Algorithms used
- Design patterns applied
- Domain-specific concepts

### 3. Visual Aids (ASCII)
```
┌─────────────┐     ┌─────────────┐
│  Component  │────▶│  Component  │
│      A      │     │      B      │
└─────────────┘     └─────────────┘
```

### 4. Examples
Provide concrete examples of:
- How to use the code
- Input/output examples
- Common use cases

### 5. Gotchas and Tips
- Non-obvious behaviors
- Common mistakes
- Performance considerations
- Related code to look at

## Explanation Style
- Start simple, add complexity
- Use analogies when helpful
- Be concrete, not abstract
- Reference specific line numbers
