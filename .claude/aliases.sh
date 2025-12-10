#!/bin/bash
# Claude Code Aliases & Profiles
# Add to your ~/.zshrc or ~/.bashrc:
#   source /path/to/puppetlabs/.claude/aliases.sh

# ============================================================
# CORE ALIASES
# ============================================================

# Standard Claude (respects permissions, prompts for dangerous ops)
alias c="claude"

# Autopilot mode (skip ALL permission prompts - use carefully!)
alias ca="claude --dangerously-skip-permissions"

# Plan mode (review changes before applying)
alias cp="claude --permission-mode plan"

# Quick one-shot commands
alias cq="claude -p"  # Single prompt, no interactive session

# ============================================================
# PROFILE ALIASES
# ============================================================

# Development profile (balanced - auto-approve safe, prompt for risky)
alias cdev="claude"

# Lab profile (full autopilot for experiments)
alias clab="claude --dangerously-skip-permissions"

# Review profile (conservative, plan mode)
alias creview="claude --permission-mode plan"

# ============================================================
# WORKFLOW SHORTCUTS
# ============================================================

# Quick code review
alias cr="claude -p '/review'"

# Ship workflow (lint, test, commit prep)
alias cship="claude -p '/ship'"

# Explain something
ce() {
  claude -p "/explain $*"
}

# Debug something
cdebug() {
  claude -p "/debug $*"
}

# Architecture design
carch() {
  claude -p "/architect $*"
}

# ============================================================
# UTILITY FUNCTIONS
# ============================================================

# Start Claude with a specific task
ctask() {
  claude -p "$*"
}

# Start Claude and immediately run tests
ctest() {
  claude -p "Run the test suite and fix any failures"
}

# Start Claude for git operations
cgit() {
  claude -p "Help me with git: $*"
}

# Resume last conversation (if supported)
alias cresume="claude --resume"

# ============================================================
# MCP SERVER MANAGEMENT
# ============================================================

# List MCP servers
alias cmcp="claude mcp list"

# Add common MCP servers
cmcp-github() {
  claude mcp add github --transport stdio -- npx -y @modelcontextprotocol/server-github
}

cmcp-fs() {
  claude mcp add filesystem --transport stdio -- npx -y @modelcontextprotocol/server-filesystem "$(pwd)"
}

# ============================================================
# TIPS
# ============================================================
#
# Quick commands:
#   c              - Start Claude normally
#   ca             - Start Claude in autopilot mode
#   cr             - Quick code review
#   cship          - Run ship workflow
#   ce <topic>     - Explain something
#   cdebug <issue> - Debug an issue
#
# Inside Claude:
#   /review        - Code review workflow
#   /ship          - Lint, test, build, commit
#   /surgery X     - Careful refactoring
#   /tests X       - Design tests
#   /architect X   - Design architecture
#   /debug X       - Systematic debugging
#   /explain X     - Deep explanation
#
# Keyboard shortcuts:
#   Tab            - Toggle extended thinking
#   Shift+Tab      - Cycle permission modes
#   Esc Esc        - Rewind conversation
#   Ctrl+C         - Cancel
#   Ctrl+L         - Clear screen
#
