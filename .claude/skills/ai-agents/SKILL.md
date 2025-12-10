---
name: ai-agents
description: Building autonomous AI agents, multi-agent systems, tool use, and agentic workflows. Use when designing agent architectures, implementing tool calling, or orchestrating multi-agent systems.
---

# AI Agents & Multi-Agent Systems Skill

## When to Use
- Designing autonomous agent architectures
- Implementing tool use / function calling
- Building multi-agent orchestration
- Creating agent memory systems
- Implementing planning and reasoning loops

## Core Agent Patterns

### ReAct Pattern (Reasoning + Acting)
```
Thought: What do I need to do?
Action: tool_name(parameters)
Observation: result from tool
Thought: What does this tell me?
... repeat until done ...
Answer: final response
```

### Tool Design Principles
1. **Single responsibility** - One tool, one job
2. **Clear schemas** - Explicit parameter types and descriptions
3. **Graceful errors** - Return useful error messages
4. **Idempotent when possible** - Safe to retry
5. **Bounded output** - Don't return entire databases

### Memory Architecture
```
Short-term: Current conversation context
Working: Scratchpad for current task
Episodic: Past interactions (vector DB)
Semantic: Knowledge base (facts, docs)
Procedural: How to do things (skills)
```

### Multi-Agent Patterns
1. **Hierarchical** - Manager delegates to specialists
2. **Collaborative** - Agents work on shared goal
3. **Adversarial** - Critic/reviewer patterns
4. **Pipeline** - Sequential handoffs
5. **Swarm** - Parallel exploration

## Implementation Checklist
- [ ] Define clear agent role/persona
- [ ] Specify available tools with schemas
- [ ] Set up memory/context management
- [ ] Implement retry/error handling
- [ ] Add observability (logging, tracing)
- [ ] Set resource limits (tokens, time, API calls)
- [ ] Handle graceful degradation

## Common Pitfalls
- **Infinite loops** - Always have termination conditions
- **Context overflow** - Summarize/compress long conversations
- **Tool abuse** - Rate limit and validate tool calls
- **Hallucinated actions** - Validate tool names exist
- **Lost context** - Implement proper memory retrieval

## Frameworks & Libraries
- **LangChain/LangGraph** - Agent orchestration
- **CrewAI** - Multi-agent teams
- **AutoGen** - Microsoft's agent framework
- **Claude Agent SDK** - Anthropic's official SDK
- **Semantic Kernel** - Microsoft's AI orchestration

## Security Considerations
- Sandbox code execution
- Validate all tool inputs
- Limit network access
- Audit trail for all actions
- Human-in-the-loop for dangerous ops
