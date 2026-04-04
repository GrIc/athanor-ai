# Athanor — Roadmap

## Phase 1 — MVP (1-2 weekends) ← CURRENT

- [ ] GCP project setup (Terraform backend, IAM, Artifact Registry)
- [ ] Deploy OpenWebUI on Cloud Run (europe-west9) with OpenRouter
- [ ] Configure family accounts (admin + 3 users)
- [ ] Set up GCP Budget Alerts (30/50/80/90/100%)
- [ ] Test mobile access (PWA)
- [ ] Connect Roo Code / Claude Code to OpenRouter

**Success criteria**: family can chat with AI models via web and mobile, cost < €10/month idle.

## Phase 2 — Integrations (month 1-2)

- [ ] Connect Home Assistant ↔ OpenWebUI (Tool or MCP)
- [ ] Activate OpenWebUI native RAG (document upload)
- [ ] Deploy Langfuse for per-user monitoring
- [ ] Deploy security pipelines (Detoxify, LLM-Guard, rate limiter)
- [ ] Activate GCP Carbon Footprint + BigQuery export
- [ ] Set up CI/CD pipeline (GitHub Actions)

## Phase 3 — Advanced RAG (month 3-6)

- [ ] Proton Drive sync via rclone → GCS → RAG ingestion
- [ ] Evaluate GraphRAG (Neo4j on Cloud Run) for relational data
- [ ] RAG on private GitHub repos
- [ ] Migrate from SQLite to Cloud SQL PostgreSQL (if needed)

## Phase 4 — Agents & Workflows (month 6-12)

- [ ] OpenWebUI agentic pipelines (function calling, tool chaining)
- [ ] NotebookLM-like workflow (doc ingestion → summaries / slides / podcasts)
- [ ] Wealth management agent (RAG on financial data + LLM reasoning)
- [ ] n8n or Temporal for complex workflow orchestration

## Phase 5 — Sensitive Data RAG (month 12+)

- [ ] Encrypted RAG pipeline (CMEK, client-side encryption)
- [ ] Health / financial / association data handling
- [ ] SecNumCloud evaluation if needed
- [ ] Security audit of full RAG chain
- [ ] Data retention policy + automatic purge