# Claude Code Configuration — Token Optimization Guide

This directory contains the Claude Code configuration for the Athanor project,
optimized to minimize token consumption while maximizing productivity.

## Architecture: 3-Tier Context System

### Tier 1 — Always Loaded (~600 tokens)
- `CLAUDE.md` (project root) — critical rules, quick start, structure, troubleshooting
- Loaded every session. Kept ruthlessly lean.

### Tier 2 — Loaded On Demand (~500-1500 tokens each)
- `.claude/skills/terraform/SKILL.md` — auto-loaded when working in `infra/`
- `.claude/skills/cloud-run/SKILL.md` — auto-loaded for Cloud Run tasks
- `.claude/skills/docker/SKILL.md` — auto-loaded for container tasks
- `docs/*.md` — referenced by Claude when needed, never loaded upfront

### Tier 3 — Never Loaded (0 tokens)
- `docs/TROUBLESHOOTING.md` — Claude reads only if a specific issue comes up
- `docs/DECISIONS.md` — ADR history, not needed in normal sessions
- Git history, changelogs

## Token Savings

| Metric | Bloated approach | This setup |
|--------|-----------------|------------|
| Startup tokens | ~2500+ | ~600 |
| Context relevance | ~25% | ~85% |
| Estimated savings | — | ~60-70% reduction |

## Key Optimizations

### 1. Lean CLAUDE.md
Under 100 lines. Only what Claude needs EVERY session. Extended docs are in `docs/` and
loaded via skills or explicit reference.

### 2. Session-Start Hook
`.claude/hooks/session-start.sh` detects your working directory and shows only relevant
context (Terraform? Docker? Docs?). Zero tokens for irrelevant info.

### 3. Skills (Progressive Disclosure)
Instead of loading all domain knowledge upfront, skills load only when Claude detects
a relevant task. Each skill is self-contained with conventions + patterns + commands.

### 4. Subagents on Haiku
- `code-reviewer` — runs on Haiku for cheap, fast code reviews
- `explorer` — runs on Haiku for read-only codebase exploration
Main session stays on Sonnet. Switch to Opus only for complex architecture decisions.

### 5. Settings Defaults
```json
{
  "model": "sonnet",                              // 80% of tasks
  "CLAUDE_AUTOCOMPACT_PCT_OVERRIDE": "50",         // Compact early, not at 95%
  "MAX_THINKING_TOKENS": "10000",                  // Cap hidden thinking cost
  "DISABLE_NON_ESSENTIAL_MODEL_CALLS": "1"         // No background token waste
}
```

### 6. Compaction Rules
CLAUDE.md includes explicit compaction instructions so critical context survives
when Claude auto-compacts the conversation.

## Usage Tips

```bash
# Start session — hook auto-detects context
claude

# For complex architecture → switch to Opus temporarily
/model opus
# ... do the complex work ...
/model sonnet

# After exploration phase → compact before implementation
/compact

# Switching to unrelated task → clear context
/clear

# Quick question without polluting context
/btw what's the default port for OpenWebUI?

# Delegate exploration to keep main context clean
"Use subagents to investigate how OpenWebUI pipelines work"
```

## File Map

```
.claude/
├── settings.json           # Model defaults, env vars, permissions
├── current-phase.txt       # Current roadmap phase (shown by hook)
├── hooks/
│   └── session-start.sh    # Dynamic context on session start
├── skills/
│   ├── terraform/SKILL.md  # TF conventions, patterns, validation
│   ├── cloud-run/SKILL.md  # Cloud Run deployment patterns
│   └── docker/SKILL.md     # Container build patterns
└── agents/
    ├── code-reviewer.md    # Haiku-based code review
    └── explorer.md         # Haiku-based codebase exploration
```