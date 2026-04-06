# Athanor — Personal AI Ecosystem on GCP

[![License: Apache 2.0](https://img.shields.io/badge/License-Apache%202.0-blue.svg)](LICENSE)
[![Status: Actively Developed](https://img.shields.io/badge/Status-Actively%20Developed-brightgreen)]()
[![GCP: Europe-West9](https://img.shields.io/badge/Hosted-GCP%20EU--West9%20Paris-orange)]()

Self-hosted family AI platform: **OpenWebUI** + **OpenRouter** + **Vertex AI** on Cloud Run (europe-west9). Scale-to-zero, OPEX-only, sovereign by design.

**Zero cost at rest. Full control. Always yours.**

---

## Why Athanor?

| Challenge | Solution |
|-----------|----------|
| AI platforms lock your data away | **Sovereign by design** — EU-hosted, self-managed, data always yours |
| Cloud costs spiral uncontrollably | **Zero cost when idle** — Cloud Run scales to zero, OpenRouter is pay-per-token |
| Vertex AI requires complex auth | **VertexAI proxy** — OpenAI-compatible sidecar, OIDC auth via service account |
| Can't share safe AI with family | **Family-first** — Multi-user RBAC, model whitelisting, parental controls (roadmap) |
| Infrastructure drift after a change | **CI/CD enforced** — Every push to `main` runs `terraform apply` automatically |

---

## Architecture

```
┌──────────────────────────────────────────────────────────────────┐
│                      CLIENTS (Any Device)                        │
│          Web Browser │ Mobile PWA │ VS Code (Roo Code)           │
└──────────────────────────────┬───────────────────────────────────┘
                               │
              ┌────────────────▼──────────────────┐
              │   GCP Cloud Run — europe-west9    │
              │                                   │
              │  ┌───────────────────────────┐    │
              │  │       OpenWebUI           │    │
              │  │  Chat · RAG · Pipelines   │    │
              │  └──────┬──────────┬─────────┘    │
              │         │          │              │
              │         ▼          ▼              │
              │   OpenRouter   VertexAI Proxy     │
              │   (200+ LLMs)  (Gemini models)    │
              │                                   │
              │  GCS Bucket · Secret Manager      │
              └───────────────────────────────────┘
                               │
              ┌────────────────▼──────────────────┐
              │  GitHub Actions → terraform apply │
              │  (triggered on every push)        │
              └───────────────────────────────────┘
```

**Key properties:**
- Scale-to-zero — €0/month at rest, cold start < 10s
- State in GCS — `gs://athanor-ai-tfstate`, versioned
- Auth via WIF — no long-lived GCP keys in CI
- Secrets in Secret Manager — nothing hardcoded

---

## Stack

| Layer | Technology |
|-------|-----------|
| Interface | OpenWebUI (React) |
| LLM routing | OpenRouter (200+ models) |
| Gemini models | VertexAI Proxy (OpenAI-compatible sidecar) |
| Compute | GCP Cloud Run (europe-west9) |
| Storage | GCS (`athanor-ai-athanor-data`) |
| IaC | Terraform + GCS backend |
| CI/CD | GitHub Actions + Workload Identity Federation |
| Secrets | GCP Secret Manager |
| Container registry | Artifact Registry (`athanor-images`) |

---

## Deploy

### CI/CD (normal path)

Every push to `main` automatically runs `terraform apply`. No manual steps.

**First-time setup** — configure these secrets in `Settings → Secrets → Actions`:

| Secret | Where to find it |
|--------|-----------------|
| `WIF_PROVIDER` | `terraform output wif_provider` |
| `WIF_SERVICE_ACCOUNT` | `terraform output cicd_service_account` |
| `TF_VAR_OPENROUTER_API_KEY` | [openrouter.ai](https://openrouter.ai) |
| `TF_VAR_WEBUI_SECRET_KEY` | `openssl rand -hex 32` |
| `TF_VAR_VERTEXAI_PROXY_API_KEY` | `openssl rand -hex 32` |
| `TF_VAR_GCP_BILLING_ACCOUNT_NAME` | GCP Console → Billing |

### Local deployment

```bash
# 1. Auth
gcloud auth login
gcloud config set project athanor-ai

# 2. Secrets
cp infra/envs/.env.prod.example infra/envs/.env.prod
# Edit .env.prod with your values, then:
source infra/envs/.env.prod

# 3. Deploy
terraform -chdir=infra init
terraform -chdir=infra apply -var-file=envs/prod.tfvars

# 4. Get your URLs
terraform -chdir=infra output
```

---

## Project Structure

```
athanor-ai/
├── .github/workflows/deploy.yml   # CI/CD — terraform apply on push
├── docker/
│   ├── openwebui/                 # Custom OpenWebUI image
│   ├── vertexai-proxy/            # OpenAI-compatible Vertex AI proxy
│   └── weekly-digest/             # Weekly parental digest (Cloud Run Job)
├── pipelines/
│   └── filters/
│       └── parental_monitor.py    # OpenWebUI filter — keyword-based alerts
├── infra/                         # Terraform (all GCP resources)
│   ├── apis.tf                    # GCP API enablement
│   ├── artifact-registry.tf       # Container registry + Cloud Build
│   ├── cloud-run.tf               # OpenWebUI + VertexAI proxy services
│   ├── gcs.tf                     # GCS buckets
│   ├── iam.tf                     # Service account permissions
│   ├── iam-cicd.tf                # WIF pool + CI service account
│   ├── monitoring.tf              # Parental monitoring (Cloud Run Job + Scheduler)
│   ├── providers.tf               # GCS backend config
│   ├── variables.tf               # Input variables
│   ├── outputs.tf                 # Service URLs, bucket names
│   └── envs/
│       ├── prod.tfvars            # Non-secret variables
│       └── .env.prod.example      # Secret variables template (local only)
├── scripts/
│   └── setup-secrets.sh           # Interactive secret setup for local deploy
└── docs/                          # Extended documentation
```

---

## Costs

OPEX-only: you pay nothing at rest.

| Usage | Cloud Run | OpenRouter | Total |
|-------|-----------|-----------|-------|
| Light (family) | €0–2 | €0–10 | **~€10/mo** |
| Moderate | €5–10 | €15–40 | **~€30/mo** |
| Intensive | €15–25 | €50–150+ | **€80+/mo** |

Free OpenRouter models (Llama, Mistral) bring family usage to near €0.

---

## Roadmap

### Phase 1 — Core infrastructure ✅
- [x] OpenWebUI + OpenRouter
- [x] Terraform IaC (Cloud Run, GCS, Secret Manager, IAM)
- [x] VertexAI proxy (Gemini models, OpenAI-compatible)
- [x] CI/CD — GitHub Actions + Workload Identity Federation
- [x] GCS Terraform state backend

### Phase 2 — Multi-user & observability
- [x] Parental monitoring (keyword alerts + weekly digest)
- [ ] PostgreSQL migration (replace SQLite)
- [ ] Langfuse monitoring (per-user cost & latency)
- [ ] Model whitelisting per user role

### Phase 3 — RAG & agents
- [ ] Document ingestion (Proton Drive, GitHub repos)
- [ ] Home Assistant integration
- [ ] Agentic workflows & function calling

---

## Troubleshooting

| Issue | Fix |
|-------|-----|
| Cloud Run 403 | Check `roles/run.invoker` IAM binding |
| Terraform state lock | `terraform force-unlock <LOCK_ID>` |
| Cold start slow | Expected at scale-to-zero; increase memory if OOM |
| OpenWebUI can't reach OpenRouter | Verify `OPENAI_API_BASE_URL` and `OPENAI_API_KEY` env vars |
| VertexAI proxy 401 | Check `PROXY_API_KEY` secret in Secret Manager |
| GCS FUSE mount fails | Check service account has `storage.objectAdmin` on bucket |

---

## Docs

See [`docs/INDEX.md`](docs/INDEX.md) for full navigation.

---

## License

Apache 2.0 — see [LICENSE](./LICENSE).
