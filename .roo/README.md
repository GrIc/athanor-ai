# Roo Code Setup — Athanor

## Context Loading

```
.roo/
├── rules/                          # Workspace-wide (ALL modes)
│   ├── 01-project.md               # Project identity + critical rules
│   └── 02-token-optimization.md    # Output efficiency rules
├── rules-code/                     # Code mode only
│   └── 01-coding-standards.md      # TF, Python, Docker, Git standards
├── rules-architect/                # Architect mode only
│   └── 01-design-principles.md     # Design principles, ADR, cost analysis
├── rules-debug/                    # Debug mode only
│   └── 01-debug-methodology.md     # Debug methodology, common commands
├── rules-terraform/                # Terraform custom mode only
│   └── 01-terraform-conventions.md # TF conventions, file structure
└── rules-reviewer/                 # Reviewer custom mode only
    └── 01-review-checklist.md      # Review checklist, output format

.roomodes                           # Custom mode definitions (3 modes)
```

## Custom Modes

| Mode | Tools | Use for |
|------|-------|---------|
| Terraform | read + edit(.tf) + command | Infrastructure changes |
| Reviewer | read only | Pre-commit code review |
| Cloud Run | read + edit(Docker/yaml/sh/py) + command | Container & deployment work |

## Token Optimization

- Workspace rules loaded for ALL modes: ~350 tokens
- Mode-specific rules loaded only when active: ~250 tokens each
- MCP disabled by default (saves ~4000 tokens/request)
- Sticky models: cheap models for Reviewer/Ask, Sonnet for Code/Debug
