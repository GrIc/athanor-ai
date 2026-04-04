# Athanor — Personal AI Ecosystem on GCP

Self-hosted family AI platform: OpenWebUI + OpenRouter on Cloud Run (europe-west9), scale-to-zero, OPEX-only.
Repo: `athanor-ai` | License: Apache 2.0 | Lang: English (code, docs, commits)

## 🚨 Critical Rules

1. **NEVER hardcode secrets** — use GCP Secret Manager or env vars. No API keys in code, ever.
2. **All GCP resources in Terraform** — no manual console clicks. Every resource must be in `infra/`.
3. **Scale-to-zero mandatory** — if a component costs money at rest, reject the approach.
4. **EU-only hosting** — `europe-west9` (Paris) or `europe-west1` (Belgium). No other regions.
5. **English only** — all code, comments, docs, commit messages in English.
6. **Commit early, commit often** — atomic commits with conventional commit messages.

## 🚀 Quick Start

```bash
# Dev setup
gcloud auth login
gcloud config set project athanor-ai
terraform -chdir=infra init

# Deploy OpenWebUI
terraform -chdir=infra apply -target=module.openwebui

# Run tests
cd infra && terraform validate && terraform plan
```

## 📁 Project Structure

```
athanor-ai/
├── infra/              # Terraform modules (GCP Cloud Run, GCS, IAM, etc.)
│   ├── modules/        # Reusable TF modules
│   ├── envs/           # Per-environment tfvars
│   └── main.tf
├── docker/             # Custom Dockerfiles (OpenWebUI extensions, Langfuse)
├── pipelines/          # OpenWebUI pipelines (Python)
├── scripts/            # Utility scripts (deploy, backup, sync)
├── docs/               # Extended documentation (see docs/INDEX.md)
└── .claude/            # Claude Code config, skills, hooks, agents
```

## 🔧 Tech Stack

| Layer | Tech |
|-------|------|
| IaC | Terraform + GCP provider |
| Runtime | Cloud Run (europe-west9) |
| Container registry | Artifact Registry |
| Database | Cloud SQL PostgreSQL (prod) / SQLite+GCS FUSE (MVP) |
| LLM routing | OpenRouter (`https://openrouter.ai/api/v1`) |
| Frontend | OpenWebUI (Docker image `ghcr.io/open-webui/open-webui:main`) |
| Secrets | GCP Secret Manager |
| Monitoring | GCP Billing API + Cloud Monitoring + Langfuse |
| CI/CD | GitHub Actions |

## 🐛 Troubleshooting

| Issue | Fix |
|-------|-----|
| Terraform state lock | `terraform force-unlock <LOCK_ID>` |
| Cloud Run cold start slow | Check min-instances=0 is expected; increase memory if OOM |
| OpenWebUI can't reach OpenRouter | Verify `OPENAI_API_BASE_URL` and `OPENAI_API_KEY` env vars |
| GCS FUSE mount fails | Check service account has `storage.objectAdmin` on bucket |

## 📐 Code Conventions

- **Terraform**: snake_case resources, `modules/` for reusable components, `envs/` for tfvars
- **Python**: black + ruff, type hints, docstrings on public functions
- **Docker**: multi-stage builds, non-root user, pinned base image tags
- **Git**: conventional commits (`feat:`, `fix:`, `infra:`, `docs:`)

## 📞 Extended Docs

See `docs/INDEX.md` for navigation. Key files:
- `docs/ARCHITECTURE.md` — full system design and diagrams
- `docs/OPENWEBUI.md` — config, pipelines, RAG setup
- `docs/FINOPS.md` — cost tracking, budget alerts, carbon footprint
- `docs/FAMILY.md` — multi-user setup, parental controls
- `docs/SECURITY.md` — IAM, secrets, data sovereignty

## ⚙️ Compaction Rules

When compacting, ALWAYS preserve:
- The full list of modified files in this session
- Any `terraform plan` output or error messages
- Current phase/task from the roadmap
- Test results and validation commands run