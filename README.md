# Athanor — Personal AI Ecosystem

**Athanor** is an open-source, self-hosted AI platform for families and DevSecOps practitioners.

Transform raw open-source bricks (OpenWebUI, OpenRouter, GCP) into a **sovereign, cost-aware, 
production-grade AI system**. Inspired by the alchemical furnace that runs continuously.

### Core Principles

- **Zero-cost at rest** — Cloud Run scales to zero, OpenRouter is pay-per-token
- **Sovereign by design** — EU-hosted on GCP, no data lock-in, full transparency
- **Family-safe** — Multi-user RBAC, parental controls, cost monitoring per account
- **DevSecOps playground** — Learn GCP, Kubernetes, CI/CD, RAG, and agents through production code
- **Completely open** — Apache 2.0, IaC-first, reproducible in one command

### What's Included

- **OpenWebUI on Cloud Run** — Web/mobile chat interface with RAG, pipelines, MCP
- **OpenRouter integration** — Access all LLM providers (Claude, GPT-4, Llama, DeepSeek…) via one API
- **Terraform IaC** — Reproducible infrastructure, secret management, cost labeling
- **Multi-user & parental controls** — RBAC, model whitelisting, conversation history retention
- **GreenOps monitoring** — Carbon footprint tracking, budget alerts, cost per user
- **Home Assistant bridge** — Control your smart home via conversational AI
- **RAG-ready** — Ingest Proton Drive documents, GitHub repos, custom sources

### Estimated Monthly Costs

| Usage | Cloud Run | OpenRouter | Total |
|-------|-----------|-----------|-------|
| Light (family tests) | ~€0–2 | €0–5 | **~€10–15** |
| Moderate (dev + family) | ~€5–10 | €10–30 | **~€25–50** |
| Intensive (daily workflow) | ~€15–25 | €50–100+ | **~€80–140+** |

**Zero cost when idle.** Scale up only when you use it.

### Quick Start
```bash
# 1. Clone and install prerequisites
git clone https://github.com/yourusername/athanor-ai
cd athanor-ai
terraform init

# 2. Set your OpenRouter API key
export OPENROUTER_API_KEY="sk-or-xxx"

# 3. Deploy to GCP
terraform apply -var="gcp_project_id=your-project"

# 4. Access OpenWebUI at https://your-cloud-run-url
```

### Documentation

- **[Architecture](./docs/ARCHITECTURE.md)** — System design, component interactions, data flow
- **[Deployment Guide](./docs/DEPLOYMENT.md)** — Step-by-step setup, GCP prerequisites, troubleshooting
- **[FinOps & GreenOps](./docs/FINOPS.md)** — Cost monitoring, carbon tracking, budget alerts
- **[Multi-user & Parental Controls](./docs/FAMILY_CONTROLS.md)** — RBAC, model whitelisting, monitoring
- **[RAG Integration](./docs/RAG.md)** — Ingest documents, Proton Drive sync, embeddings
- **[Home Assistant Integration](./docs/HOME_ASSISTANT.md)** — Control your smart home via AI

### Stack

- **Frontend** — OpenWebUI (React, self-hosted)
- **LLM Routing** — OpenRouter (SaaS, pay-per-token)
- **Infrastructure** — GCP Cloud Run, Cloud SQL, GCS
- **IaC** — Terraform / Terragrunt
- **CI/CD** — GitHub Actions
- **Monitoring** — GCP Billing API, Carbon Footprint, Langfuse (optional)
- **IDE Integration** — Roo Code, Cline (via OpenRouter)
- **Domotics** — Home Assistant (Raspberry Pi bridge)

### For Whom?

- **DevSecOps engineers** — Learn GCP, serverless, observability, and IaC in a real project
- **Families** — Private, cost-controlled AI for homework help, creative projects, coding
- **Privacy advocates** — EU-hosted, encrypted data handling, full audit logs
- **AI/ML practitioners** — Playground for RAG, agentic workflows, multi-provider LLM routing

### License

Apache License 2.0 — See [LICENSE](./LICENSE)

### Contributing

Contributions welcome! Please read [CONTRIBUTING.md](./CONTRIBUTING.md) before submitting PRs.

---

**Status** : Actively developed | **Last Updated** : [DATE]
