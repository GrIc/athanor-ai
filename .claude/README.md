# Claude Code Configuration — Athanor

## 3-Tier Context System

### Tier 1 — Always Loaded (~600 tokens)
- `CLAUDE.md` — critical rules, quick start, structure, troubleshooting

### Tier 2 — Loaded On Demand
- `.claude/skills/terraform/SKILL.md` — auto-loaded for `infra/` work
- `.claude/skills/cloud-run/SKILL.md` — auto-loaded for Cloud Run tasks
- `.claude/skills/docker/SKILL.md` — auto-loaded for container tasks

### Tier 3 — Read When Needed
- `docs/*.md` — referenced by Claude on demand

## Subagents

| Agent | Model | Purpose |
|-------|-------|---------|
| `code-reviewer` | Haiku | Post-change review (security, EU, scale-to-zero) |
| `explorer` | Haiku | Read-only codebase exploration |

## File Map

```
.claude/
├── settings.json           # Model defaults, env vars, permissions
├── current-phase.txt       # Current roadmap phase
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
