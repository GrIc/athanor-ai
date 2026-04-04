# Roo Code Setup — Token Optimization for Athanor

## How Roo Code loads context

Unlike Claude Code (which has `CLAUDE.md` + skills + hooks), Roo Code injects context via:

1. **System prompt** (built-in, per mode) — you can't change this
2. **Global rules** (`~/.roo/rules/`) — loaded for ALL modes, ALL projects
3. **Workspace rules** (`.roo/rules/`) — loaded for ALL modes in this project
4. **Mode-specific rules** (`.roo/rules-{slug}/`) — loaded ONLY for that mode
5. **Custom mode definitions** (`.roomodes`) — roleDefinition + customInstructions
6. **MCP tool descriptions** — ~16k chars if enabled (disable if not using!)

Every rule file is appended to the system prompt as tokens. **More rules = more tokens per request.**

## Optimization Strategy

### 1. Lean Workspace Rules (~350 tokens)

`.roo/rules/` contains only 2 files loaded for EVERY mode:
- `01-project.md` — project identity, critical rules, structure, tech stack
- `02-token-optimization.md` — output efficiency, context management, scope discipline

These are the equivalent of Claude Code's Tier 1 CLAUDE.md.

### 2. Mode-Specific Rules (loaded only when needed)

Each mode has its own rules directory, loaded ONLY when that mode is active:
- `.roo/rules-code/` — coding standards (Terraform, Python, Docker, Git)
- `.roo/rules-architect/` — design principles, ADR format, cost analysis
- `.roo/rules-debug/` — debug methodology, common commands
- `.roo/rules-terraform/` — TF conventions, module structure, validation
- `.roo/rules-reviewer/` — review checklist, output format

**Savings**: When in Architect mode, you don't pay for Code mode's rules, and vice versa.

### 3. Custom Modes with Restricted Tool Groups

`.roomodes` defines 3 project-specific modes with restricted tools:

| Mode | Tools | Why restricted |
|------|-------|---------------|
| 🏗️ Terraform | read + edit(.tf only) + command | Can't accidentally edit non-TF files |
| 🔍 Reviewer | read only | Can't modify files during review |
| 🐳 Cloud Run | read + edit(Docker/yaml/sh) + command | Scoped to container files |

**Savings**: Fewer tool descriptions in system prompt = fewer tokens per request.

### 4. Sticky Models (Cost-Tiered)

Roo Code remembers the last model per mode. Set once, saves every session:

| Mode | Recommended Model | Cost | Rationale |
|------|------------------|------|-----------|
| 🏗️ Architect | Claude Sonnet 4.6 | $$ | Planning needs quality |
| 💻 Code | Claude Sonnet 4.6 | $$ | Default workhorse |
| ❓ Ask | DeepSeek V3 / free | ¢ | Just answering questions |
| 🐛 Debug | Claude Sonnet 4.6 | $$ | Needs reasoning |
| 🔍 Reviewer | DeepSeek V3 / Llama | ¢ | Read-only, simple checks |
| 🏗️ Terraform | Claude Sonnet 4.6 | $$ | Precision matters |
| 🐳 Cloud Run | Claude Sonnet 4.6 | $$ | Container expertise |

### 5. Max Output Tokens per Mode

In Roo Code profile settings, cap output tokens per mode:
- **Code**: 16k (most edits are small)
- **Architect**: 32k (planning can be verbose)
- **Debug**: 32k (may need detailed analysis)
- **Reviewer**: 8k (just a checklist)
- **Ask**: 8k (just Q&A)

This caps hidden thinking token costs.

### 6. MCP Discipline

**Disable MCP globally unless actively using it.** MCP server descriptions add ~16k
characters to EVERY system prompt, even if you never call an MCP tool.

Enable per-session only when needed (e.g., for GitHub MCP, Home Assistant MCP).

## File Map

```
.roo/
├── rules/                          # Workspace-wide (ALL modes)
│   ├── 01-project.md               # Project identity + critical rules (~200 tokens)
│   └── 02-token-optimization.md    # Output efficiency rules (~150 tokens)
├── rules-code/                     # Code mode only
│   └── 01-coding-standards.md      # TF, Python, Docker, Git standards
├── rules-architect/                # Architect mode only
│   └── 01-design-principles.md     # Design principles, ADR, cost analysis
├── rules-debug/                    # Debug mode only
│   └── 01-debug-methodology.md     # Debug methodology, common commands
├── rules-terraform/                # Terraform custom mode only
│   └── 01-terraform-conventions.md # TF conventions, module structure
└── rules-reviewer/                 # Reviewer custom mode only
    └── 01-review-checklist.md      # Review checklist, output format

.roomodes                           # Custom mode definitions (3 modes)
.vscode/settings.json               # VSCode + Roo Code recommended settings
```

## Usage Tips

```
# Start planning → Architect mode (read-only, quality model)
/architect Design the Terraform module for Cloud Run OpenWebUI deployment

# Switch to implement → Code mode (full tools, Sonnet)
/code Implement the cloud-run module based on the architect plan

# Quick review before commit → Reviewer mode (read-only, cheap model)
/reviewer Review the changes in infra/modules/cloud-run/

# Infrastructure only → Terraform mode (restricted to .tf files)
/terraform Add budget alert module to infra/modules/monitoring/

# Debug an issue → Debug mode (read + command, Sonnet)
/debug OpenWebUI returns 503 after deploy, check Cloud Run logs

# Quick question → Ask mode (read-only, cheapest model)
/ask What's the OpenWebUI env var for disabling signup?
```

## Estimated Token Savings

| Metric | No optimization | This setup |
|--------|----------------|------------|
| Rules per Code session | ~all rules loaded | ~350 (global) + ~250 (mode) tokens |
| Rules per Review session | ~all rules loaded | ~350 (global) + ~200 (mode) tokens |
| MCP overhead (disabled) | ~4000 tokens | 0 tokens |
| Max thinking tokens | uncapped | capped per mode |
| Model cost per review | Sonnet/Opus | DeepSeek (10-50x cheaper) |
| **Overall reduction** | — | **~50-60% per session** |
