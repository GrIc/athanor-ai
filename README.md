# Athanor — Personal AI Ecosystem

[![License: Apache 2.0](https://img.shields.io/badge/License-Apache%202.0-blue.svg)](LICENSE)
[![Status: Actively Developed](https://img.shields.io/badge/Status-Actively%20Developed-brightgreen)]()
[![GCP: Europe-West9](https://img.shields.io/badge/Hosted-GCP%20EU-orange)]()

Transform raw open-source bricks (OpenWebUI, OpenRouter, GCP) into a **sovereign, cost-aware, production-grade AI system**. Athanor is a self-hosted AI platform for families and DevSecOps practitioners—inspired by the alchemical furnace that runs continuously.

**Zero cost at rest. Full control. Always yours.**

---

## 🎯 Why Athanor?

| Challenge | Solution |
|-----------|----------|
| AI platforms lock your data away | **Sovereign by design** — EU-hosted, self-managed, data always yours |
| Cloud costs spiral uncontrollably | **Zero cost when idle** — Cloud Run scales to zero, OpenRouter is pay-per-token |
| Can't share safe AI with family | **Family-first** — Multi-user RBAC, model whitelisting, parental controls |
| DevOps requires learning on the fly | **Learning playground** — GCP, Terraform IaC, CI/CD, observability, FinOps in practice |
| AI infrastructure feels overwhelming | **One command to deploy** — Terraform IaC, reproducible, auditable, documented |

---

## ⚡ Core Principles

- **Zero-cost at rest** — Cloud Run scales to zero when idle; OpenRouter charges only per token used
- **Sovereign by design** — EU-hosted on GCP (europe-west9), no vendor lock-in, full audit trails
- **Family-safe** — Multi-user RBAC, model whitelisting, conversation history retention, cost monitoring
- **DevSecOps learning** — Real production infrastructure to master GCP, Terraform, observability, FinOps/GreenOps
- **Completely open** — Apache 2.0, IaC-first, reproducible, transparent, community-driven

---

## 📦 What's Included

### Core Features
- **OpenWebUI on Cloud Run** — Web and mobile chat interface with RAG, pipelines, and MCP support
- **OpenRouter integration** — Single API endpoint for 200+ LLM models (Claude, GPT-4, Llama, DeepSeek, etc.)
- **Terraform IaC** — Infrastructure as code: reproducible, versioned, auditable, documented
- **Multi-user RBAC** — Admin, user, and restricted roles with per-user model whitelisting
- **Persistent storage** — Google Cloud Storage (GCS) for files, embeddings, backups

### Security & Observability
- **Secret management** — All credentials in GCP Secret Manager, never in code or env vars
- **IAM least privilege** — Minimal required permissions on Cloud Run service account
- **Audit logging** — Cloud Logging captures all API requests and user actions
- **GCP cost tracking** — Real-time monitoring with budget alerts (30%, 50%, 80%, 90%, 100%)
- **Carbon footprint** — Track environmental impact via GCP Carbon Footprint API

### Advanced (Roadmap)
- **RAG-ready** — Framework for ingesting Proton Drive, GitHub repos, custom documents
- **Home Assistant bridge** — Control smart home via conversational AI interface
- **Agentic workflows** — Multi-step agents, function calling, autonomous tasks
- **Langfuse monitoring** — Cost and performance analytics per user (optional)

---

## 🚀 Quick Start

### Prerequisites
- Google Cloud Platform account with billing enabled
- `gcloud` CLI installed and authenticated
- Terraform >= 1.5.0
- OpenRouter API key (free account at [openrouter.ai](https://openrouter.ai))

### Deploy in 5 Steps

```bash
# 1. Clone the repository
git clone https://github.com/GrIc/athanor-ai.git
cd athanor-ai/terraform

# 2. Copy and configure
cp terraform.tfvars.example terraform.tfvars
# Edit terraform.tfvars with:
#   project_id         = "your-gcp-project-id"
#   gcp_region         = "europe-west9"
#   openrouter_api_key = "sk-or-v1-xxx"
#   webui_secret_key   = "$(openssl rand -hex 32)"
#   gcp_billing_account_name = "My Billing Account"

# 3. Deploy
terraform init
terraform plan
terraform apply

# 4. Get your URL
terraform output openwebui_url

# 5. Open in browser and sign up (first user becomes admin)
```

**That's it!** Your instance is live and auto-scaling to zero when idle.

---

## 💰 Costs

Athanor is **OPEX-first**: you only pay for what you use. No fixed costs.

### Monthly Cost Estimates

| Usage Tier | Cloud Run | OpenRouter | Total | Best For |
|-----------|-----------|-----------|-------|----------|
| **Light** | €0–2 | €0–10 | **€10–15** | Family, testing, free models |
| **Moderate** | €5–10 | €15–40 | **€25–50** | Dev + family mix |
| **Intensive** | €15–25 | €50–150+ | **€80–200+** | Daily professional use |

### Cost Breakdown

| Service | Rate | Condition |
|---------|------|-----------|
| Cloud Run | €0.0000025/vCPU-second | Charged only during requests |
| GCS Storage | €0.020/GB/month | Files + embeddings |
| OpenRouter | Per token | Only when querying LLMs |
| Secret Manager | Free | Storing API keys |
| **Idle instance** | **€0.00/month** | **24/7 at no cost** |

**💡 Pro tip**: Use free OpenRouter models (Llama 3.1, Mistral) for family members to minimize costs.

---

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                     CLIENTS (Any Device)                        │
│  VSCode (Roo Code) │ Web Browser │ Mobile PWA │ Home Assistant  │
└────────────────────────────┬────────────────────────────────────┘
                             │
                      OpenRouter API
                   (single unified endpoint)
                             │
        ┌────────────────────┼────────────────────┐
        ▼                    ▼                    ▼
    Claude Opus          GPT-4o              Llama 3.1
    + 200+ models from Anthropic, OpenAI, Google, Meta, DeepSeek, xAI...
        │                    │                    │
        └────────────────────┼────────────────────┘
                             │
        ┌────────────────────▼────────────────────┐
        │   OpenRouter Proxy (routing + rate limit)
        └────────────────────┬────────────────────┘
                             │
        ┌────────────────────▼────────────────────┐
        │  GCP Cloud Run (europe-west9 / Paris)   │
        │                                         │
        │  ┌─────────────────────────────────┐    │
        │  │     OpenWebUI Container         │    │
        │  │  • Web/mobile chat interface    │    │
        │  │  • RAG engine (ChromaDB)        │    │
        │  │  • Pipelines & Functions        │    │
        │  │  • Multi-user RBAC              │    │
        │  └──────────────┬──────────────────┘    │
        │                 │                       │
        │    ┌────────────┼────────────┐          │
        │    ▼            ▼            ▼          │
        │  GCS Bucket  PostgreSQL  Secret Mgr     │
        │  (data)      (users)     (credentials)  │
        │                                         │
        └────────────────┬────────────────────────┘
                         │
        ┌────────────────┼────────────────────┐
        ▼                ▼                    ▼
    GCP Billing     Cloud Monitoring   Carbon Footprint
    (cost tracking) (logs & metrics)   (environmental)
```

**Key insight**: Scale-to-zero means your instance costs €0/month when nobody is using it. Spins up in <10 seconds on first request.

---

## 📚 Documentation

Complete guides for every aspect:

| Document | Focus |
|----------|-------|
| **[ARCHITECTURE.md](./docs/ARCHITECTURE.md)** | System design, component interactions, data flow, scaling decisions |
| **[DEPLOYMENT.md](./docs/DEPLOYMENT.md)** | Step-by-step setup, GCP prerequisites, troubleshooting, customization |
| **[FINOPS.md](./docs/FINOPS.md)** | Cost monitoring, budget alerts, carbon tracking, optimization |
| **[FAMILY_CONTROLS.md](./docs/FAMILY_CONTROLS.md)** | RBAC, model whitelisting, parental monitoring, history retention |
| **[RAG.md](./docs/RAG.md)** | Document ingestion, Proton Drive sync, embeddings, vector databases |
| **[HOME_ASSISTANT.md](./docs/HOME_ASSISTANT.md)** | Smart home automation, Raspberry Pi integration, MCP tools |

---

## 🛠️ Tech Stack

| Layer | Technology | Purpose |
|-------|-----------|---------|
| **Interface** | OpenWebUI (React) | Web/mobile chat, RAG, pipelines |
| **LLM Routing** | OpenRouter | Unified API for 200+ models |
| **Compute** | GCP Cloud Run | Serverless, auto-scaling, zero when idle |
| **Storage** | GCS + PostgreSQL | Files, embeddings, audit logs |
| **Infrastructure** | Terraform | IaC, reproducible, version-controlled |
| **CI/CD** | GitHub Actions | Automated deployment, compliance checks |
| **Monitoring** | GCP APIs, Langfuse (opt.) | Costs, logs, metrics, LLM analytics |
| **Secrets** | GCP Secret Manager | Secure credential storage |
| **Smart Home** | Home Assistant (Raspberry Pi) | Local automation bridge |

---

## 👥 For Whom?

### 👨‍💻 **DevSecOps Engineers & SREs**
Learn GCP, serverless architecture, IaC, observability, and FinOps in a real production environment. Master Cloud Run, Secret Manager, IAM, and monitoring tools.

### 👨‍👩‍👧‍👦 **Families**
Private, cost-controlled AI for homework help, creative projects, coding assistance, and smart home automation. Multi-user RBAC ensures everyone stays safe.

### 🔐 **Privacy Advocates**
EU-hosted infrastructure, end-to-end encryption, full audit logs, zero vendor lock-in. Your data never leaves your control.

### 🧠 **AI/ML Practitioners**
Production-grade playground for RAG, agentic workflows, multi-provider LLM routing, and prompt engineering. Learn what works at scale.

---

## 🗺️ Roadmap

### Phase 1 — MVP ✅ (Current)
- [x] OpenWebUI + OpenRouter integration
- [x] Terraform IaC deployment
- [x] Multi-user RBAC
- [x] GCP cost monitoring
- [ ] PostgreSQL migration (in progress)

### Phase 2 (Q2 2025)
- [ ] RAG: Document ingestion (Proton Drive, GitHub)
- [ ] Home Assistant integration
- [ ] Langfuse monitoring & per-user analytics
- [ ] Parental controls & content filtering

### Phase 3 (Q3 2025)
- [ ] GraphRAG for knowledge graphs
- [ ] Agentic workflows & function calling
- [ ] Carbon footprint dashboard
- [ ] Advanced multi-agent orchestration

### Phase 4 (Q4 2025+)
- [ ] Custom model fine-tuning interface
- [ ] Workflow orchestration (n8n / Temporal)
- [ ] SecNumCloud compliance certification
- [ ] Community ecosystem & plugins

---

## ⚠️ Important Notes

### Security
- **Never commit credentials** — Use `terraform.tfvars.example` as template
- **Secret Manager required** — All API keys must be in GCP Secret Manager
- **RBAC enforcement** — Assign users minimum required roles only
- **Audit logs** — Cloud Logging records all API calls; review regularly

### Known Limitations
- **SQLite concurrency** — MVP uses SQLite; production needs PostgreSQL for concurrent users
- **Data retention** — Conversations are logged by default; implement deletion policies for compliance
- **Rate limiting** — OpenRouter enforces per-account limits (see their docs)
- **Uptime dependency** — Service stability depends on OpenRouter's API availability

### Compliance
- **GDPR** — Data stored on GCP EU; implement data subject deletion procedures
- **Children's data** — Comply with COPPA (US) / GDPR (EU) if using with minors
- **Terraform state** — Keep `.gitignore`d locally; store remotely in GCS with versioning

---

## 💡 Tips & Tricks

### Cost Optimization
```bash
# Monitor costs weekly
terraform output cloud_run_url
# Check GCP Console → Billing

# Use free models for non-critical tasks
# Llama 3.1, Mistral are free on OpenRouter

# Set up budget alerts
# GCP Console → Billing → Budget alerts
```

### Performance
```bash
# Faster responses: add :nitro suffix to model names
# Minimum cost: add :floor suffix

# Batch requests when possible (RAG, document processing)
```

### Team Setup
```bash
# Use Terraform workspaces for staging/prod
terraform workspace new staging
terraform apply -var="environment=staging"
```

---

## 📄 License

Athanor is licensed under the **Apache License 2.0** — see [LICENSE](./LICENSE) for details.

- ✅ Use commercially
- ✅ Modify and distribute (with attribution)
- ⚠️ No warranty provided
- ⚠️ Must include original license

---

## 🤝 Contributing

Contributions welcome! Whether bug fixes, documentation, new features, or deployment improvements.

**How to contribute:**
1. Read [CONTRIBUTING.md](./CONTRIBUTING.md)
2. Fork the repo
3. Create a feature branch (`git checkout -b feature/your-feature`)
4. Test locally
5. Submit a PR with clear description

**Types of contributions we need:**
- 🐛 Bug fixes & optimizations
- 📖 Documentation & examples
- 🏗️ Architecture improvements
- 🚀 New features (RAG, agents, integrations)
- 🌍 Translations & localization

---

## 🙋 Support

- **Issues** — Report bugs or request features via GitHub Issues
- **Discussions** — Ask questions, discuss ideas, share experiences
- **Pull Requests** — Submit improvements (see CONTRIBUTING.md)
- **Documentation** — Contribute guides and best practices

---

## 📊 Project Status

| Component | Status |
|-----------|--------|
| Core deployment | ✅ Production-ready |
| Multi-user RBAC | ✅ Working |
| Cost monitoring | ✅ GCP Billing API active |
| RAG integration | 🏗️ In development |
| Home Assistant | 🏗️ Integration planned |
| Langfuse | 📋 Queued |
| Carbon tracking | ✅ Ready |

**Last updated**: April 2025 | **Actively maintained**

---

## 🎓 What You'll Learn

By deploying and maintaining Athanor, you'll master:

**Cloud Infrastructure**
- GCP Cloud Run (serverless compute)
- Google Cloud Storage (persistent data)
- Cloud SQL (database)
- Cloud Monitoring & Logging
- IAM & Secret Manager

**DevOps & IaC**
- Terraform (infrastructure as code)
- GitHub Actions (CI/CD)
- Container deployment
- Infrastructure versioning

**Architecture & Design**
- Serverless design patterns
- Scale-to-zero architecture
- OPEX-first thinking
- Cost-aware infrastructure

**FinOps & Sustainability**
- Cloud cost tracking & optimization
- Budget alerts & forecasting
- Carbon footprint measurement
- Sustainable infrastructure

**AI/ML**
- RAG (Retrieval-Augmented Generation)
- Vector embeddings
- Multi-model LLM routing
- Prompt engineering
- Agentic workflows

---

## 🙏 Acknowledgments

Built on the work of amazing communities:

- [OpenWebUI](https://github.com/open-webui/open-webui) — Open-source chat interface
- [OpenRouter](https://openrouter.ai) — LLM aggregation & routing
- [Google Cloud Platform](https://cloud.google.com) — Cloud infrastructure
- [Terraform](https://www.terraform.io) — Infrastructure as code
- [Home Assistant](https://www.home-assistant.io) — Home automation
- DevSecOps & AI communities — Inspiration & feedback

---

<p align="center">
  <strong>Transform raw open-source bricks into a sovereign, production-grade AI system.</strong>
  <br/>
  <em>The alchemical furnace that runs continuously.</em>
  <br/>
  <br/>
  Made with ❤️ for families, practitioners, and builders.
</p>