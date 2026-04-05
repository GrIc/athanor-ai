# Athanor — Roadmap

> Last updated: 2026-04-05

---

## Phase 1 — Core Infrastructure ✅ DONE

- [x] GCP project setup (Terraform backend on GCS, IAM, Artifact Registry)
- [x] Deploy OpenWebUI on Cloud Run (europe-west9) with OpenRouter
- [x] Add VertexAI Proxy as sovereign channel for Gemini models (ADR-004)
- [x] CI/CD pipeline: GitHub Actions + Workload Identity Federation
- [x] GCS FUSE for persistent OpenWebUI data (SQLite)
- [x] GCP Budget Alerts (30/50/80/90/100%)
- [x] Secret management via GCP Secret Manager

**Result**: Working platform. Push to main → terraform apply → images rebuilt → services updated. Zero manual intervention.

---

## Phase 2 — Family & Observability ← CURRENT

### 2a. Family accounts & parental controls
- [ ] Configure family accounts in OpenWebUI (admin + 3 users)
- [ ] Model whitelisting per user (restrict teens to Gemini Flash / free models)
- [ ] Conversation monitoring pipeline — weekly digest of teens' AI usage (topics, time, volume)
- [ ] Rate limiting per user (daily token budget)
- [ ] Test mobile access (PWA) and family onboarding

### 2b. FinOps & GreenOps
- [ ] Langfuse deployment on Cloud Run (LLM observability, scale-to-zero)
- [ ] Per-user cost tracking: OpenRouter spend + VertexAI spend → dashboard
- [ ] GCP Carbon Footprint API activation + export to BigQuery
- [ ] Monthly cost & carbon report (automated email or OpenWebUI pipeline)

### 2c. Database migration
- [ ] Migrate SQLite → Cloud SQL PostgreSQL (concurrent multi-user access)
- [ ] Evaluate AlloyDB Omni as cheaper alternative

**Success criteria**: Family actively using the platform. Each user has a cost & usage dashboard. Teens monitored without intrusion.

---

## Phase 3 — Family Projects & Collaboration

### 3a. Shared project spaces
- [ ] OpenWebUI workspace/channel per family project (e.g., "Dressing project", "Holiday planning")
- [ ] Shared context per project (documents, notes, decisions)
- [ ] Couple-only projects with restricted access

### 3b. Daily assistant agents
- [ ] **Email synthesizer** — summarize daily emails (Gmail API or IMAP) into morning briefing
- [ ] **Agenda manager** — parse Google Calendar, suggest daily priorities, detect conflicts
- [ ] **Household task tracker** — recurring tasks, assignments, reminders via OpenWebUI chat

### 3c. Home Assistant integration
- [ ] Home Assistant ↔ OpenWebUI bridge (MCP or custom tool)
- [ ] Voice commands: "Turn off the lights in the kids' rooms"
- [ ] Automation suggestions: "The heating was on while nobody was home for 3 hours"
- [ ] Energy consumption reports via conversational interface

**Success criteria**: Family uses AI daily for practical tasks. Home automation controllable by voice or chat.

---

## Phase 4 — RAG & Knowledge Base

### 4a. Document RAG
- [ ] Proton Drive sync: rclone → GCS → RAG ingestion pipeline
- [ ] Family document search (insurance, contracts, school documents, recipes)
- [ ] Photo search & tagging via multimodal RAG (Gemini vision)

### 4b. Domain-specific RAG
- [ ] GitHub repos RAG (personal and professional)
- [ ] Bookmark/article RAG — save web articles, ask questions later

### 4c. Advanced RAG
- [ ] Evaluate GraphRAG (Neo4j on Cloud Run) for relational family knowledge
- [ ] Hybrid search: vector + keyword + graph
- [ ] RAG evaluation pipeline (precision, recall, hallucination rate)

**Success criteria**: "Find our home insurance contract" or "What was the recipe for grandma's cake?" works from chat.

---

## Phase 5 — Specialized Agents

### 5a. Wealth & property management
- [ ] **Wealth manager agent** — RAG on financial docs (bank statements, tax returns, investments) + LLM reasoning
- [ ] Portfolio analysis: allocation, risk, performance tracking
- [ ] Tax optimization suggestions (French tax context)
- [ ] Property value tracking (estimated value, market trends)

### 5b. Home renovation assistant
- [ ] **Architect/renovation agent** — RAG on floor plans, quotes, regulations
- [ ] Budget tracker for renovation projects
- [ ] Contractor comparison and recommendation engine
- [ ] Planning permit assistant (French urban planning rules)

### 5c. Education & learning
- [ ] **Homework helper agent** — curriculum-aware (French Brevet/Bac), explains step-by-step
- [ ] Flashcard generator from course notes (RAG on teens' documents)
- [ ] Essay reviewer with age-appropriate feedback

**Success criteria**: Agents that understand our specific family data and give actionable, personalized advice.

---

## Phase 6 — Security & Compliance (month 12+)

- [ ] Encrypted RAG pipeline (CMEK + client-side encryption for sensitive docs)
- [ ] Data classification: public / family / sensitive / financial
- [ ] Automatic routing: sensitive → VertexAI only, general → OpenRouter
- [ ] Data retention policies + automatic purge (GDPR)
- [ ] Security audit of full RAG chain
- [ ] Evaluate SecNumCloud if professional use grows

---

## Phase 7 — Advanced Platform (long-term vision)

### Workflow orchestration
- [ ] n8n or Temporal on Cloud Run for multi-step automations
- [ ] "When an invoice arrives by email → extract data → update budget → notify me"
- [ ] "When kids finish homework → check calendar → suggest activity"

### Multi-modal & creative
- [ ] Image generation pipeline (Imagen on VertexAI or open-source)
- [ ] Voice interface (Whisper STT → LLM → TTS) for hands-free kitchen/workshop use
- [ ] Podcast/summary generator from family documents (NotebookLM-style)

### Community & sharing
- [ ] Open-source pipeline library (share useful pipelines with OpenWebUI community)
- [ ] Template for "family AI setup" that others can fork
- [ ] Blog/documentation of the journey

### Platform evolution
- [ ] Fine-tuned models on family writing style (for drafting personal messages)
- [ ] Local inference option (Ollama on NUC) for offline/privacy-critical tasks
- [ ] Federation: connect multiple Athanor instances (e.g., extended family)
- [ ] Cost prediction: "This query will cost approximately €0.03, proceed?"

---

## Principles Across All Phases

| Principle | Enforcement |
|-----------|------------|
| Zero cost at rest | Every new service must scale-to-zero |
| EU sovereign | No data leaves europe-west9 unless explicitly allowed |
| No manual deploys | Everything via terraform apply triggered by CI/CD |
| Secrets in Secret Manager | Never in code, env files, or CI logs |
| Observable | Every new service gets Langfuse + cost tracking from day 1 |
| Family-safe | Parental controls on every user-facing feature |
