# Athanor — Roadmap

> Last updated: 2026-04-09

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

## Phase 2 — Family & Observability ✅ DONE

### 2a. Family accounts & parental controls
- [x] Configure family accounts in OpenWebUI (admin + 3 users) — *manual setup, see [FAMILY_SETUP.md](FAMILY_SETUP.md)*
- [x] Model whitelisting per user (restrict teens to Gemini Flash / free models) — *manual via OpenWebUI Admin*
- [x] Conversation monitoring pipeline — weekly digest of teens' AI usage (topics, time, volume)
- [x] Budget tracking per user (€2/week default, auto-refresh prices from OpenRouter API)
- [x] Test mobile access (PWA) and family onboarding

### 2b. FinOps & GreenOps
- [ ] Langfuse deployment on Cloud Run (LLM observability, scale-to-zero) — *DEFERRED, use OpenWebUI built-in analytics*
- [x] Per-user cost tracking: budget filter + cost dashboard on Cloud Run (scale-to-zero)
- [x] GCP Carbon Footprint data available via billing export in Cloud Console (no separate API)
- [x] Monthly cost report (automated email or OpenWebUI pipeline)

### 2c. Database migration — DEFERRED
- [ ] Migrate SQLite → Cloud SQL PostgreSQL (concurrent multi-user access) — *deferred, too expensive for now*
- [ ] Evaluate AlloyDB Omni as cheaper alternative

**Success criteria**: ✅ Family actively using the platform. Each user has a cost & usage dashboard. Teens monitored without intrusion. Budget enforced at €2/week per user.

---

## Phase 3 — RAG & Knowledge Base ← CURRENT

> Full implementation spec: [RAG_IMPLEMENTATION.md](RAG_IMPLEMENTATION.md) | Architecture review: [Architecture-review-9-04-2026.md](Architecture-review-9-04-2026.md)

**Design constraints** (non-negotiable from day 1):
- Proton Drive folders marked with `athanor.{name}` files → auto-discovered projects
- Documents downloaded ephemerally to `/tmp/`, destroyed after ingest — **never stored on GCS**
- ChromaDB: `EphemeralClient` only, snapshots as `json.gz` on GCS (no SQLite-on-FUSE)
- All LLM/embedding calls via VertexAI Proxy — never OpenRouter
- CMEK: Cloud KMS Customer-Managed keys for both GCS buckets
- GraphRAG (NetworkX) is opt-in via `graph_enabled: true` in marker file YAML

**Architecture**:
```
Proton Drive (athanor.* marker files)
  → athanor-ingest (Cloud Run Job, daily 03:00)
      → ephemeral /tmp/ download → parse → embed → GCS snapshot
  → GCS athanor-ai-rag-data (.vectordb/*.json.gz, checkpoints/*.md, manifest.json)
  → athanor-rag (Cloud Run Service, scale-to-zero)
      → EphemeralClient loaded from GCS → /api/search, /v1/chat/completions
  → OpenWebUI Pipe (one per project, auto-registered from manifest)
```

### 3a. Core Libraries ← NEXT

- [ ] `lib/connectors/base.py` — DriveConnector ABC + ProjectInfo + ConnectorError + get_connector()
- [ ] `lib/rag_core/client.py` + `embeddings.py` — ResilientClient (VertexAI Proxy) with chat_multimodal()
- [ ] `lib/rag_core/store.py` — VectorStore: EphemeralClient + save/load GCS json.gz
- [ ] `lib/rag_core/ocr.py` — OcrProcessor: Gemini Flash 2.5 multimodal (configurable via OCR_MODEL)
- [ ] `lib/rag_core/ingest.py` — parse_document(): PDF/DOCX/PPTX/MD/images → chunks
- [ ] `lib/rag_core/graph*.py` — KnowledgeGraph, TripletExtractor (generic LLM), HybridSearcher
- [ ] `lib/agents/` — BaseAgent + render_system_prompt() + agents/defs/default.md

**Validation**: `python -c "from lib.rag_core.store import VectorStore; print('OK')"` for each module.

### 3b. Proton Drive Connector

- [ ] `lib/connectors/proton.py` — ProtonDriveConnector via rclone subprocess
  - `list_projects()`: scan for `athanor.*`, parse YAML content (empty = defaults)
  - `download_project_files()`: rclone copy to `/tmp/ingest/{project}/`, exclude `.athanor/` and `athanor.*`
  - `delete_temp_files()`: `shutil.rmtree()` in `finally`
  - `upload_checkpoint()` / `read_checkpoint()`: write to `{folder}/.athanor/checkpoint.md`
- [ ] `docs/CONNECTORS.md` — DriveConnector ABC interface + rclone setup guide

**Validation**: test with local rclone.conf + real Proton Drive folder containing an `athanor.test` file.

### 3c. Ingest Job

- [ ] `docker/athanor-ingest/ingest_job.py` — full flow: discover → download → parse → embed → snapshot → backup
  - feeds_into: chunks from source project added to target collection at write time
  - backup: `gcloud storage cp` to `athanor-ai-rag-backup/{YYYY-MM-DD}/` after success
- [ ] `docker/athanor-ingest/Dockerfile` — python:3.12-slim + rclone (no Tesseract)
- [ ] `docker/athanor-ingest/requirements.txt`

**Validation**: `docker build` → exit 0 → GCS shows `.vectordb/test.json.gz`, no PDFs on GCS.

### 3d. RAG Service

- [ ] `docker/athanor-rag/main.py` — FastAPI + lifespan (load all snapshots from GCS at startup)
- [ ] Routes: `/health`, `/api/projects`, `/api/projects/{name}/search`, `/v1/chat/completions`, `/api/projects/{name}/checkpoint`, `/api/reload`, `/ingest/trigger`
- [ ] `docker/athanor-rag/Dockerfile` — python:3.12-slim (no rclone, no Tesseract)

**Validation**: `curl /health` → 200 with project list + chunk counts.

### 3e. Terraform

- [ ] `infra/kms-rag.tf` — Cloud KMS keyring + crypto key (europe-west9, 90-day rotation)
- [ ] `infra/gcs-rag.tf` — `athanor-ai-rag-data` (Standard) + `athanor-ai-rag-backup` (Nearline), both CMEK
- [ ] `infra/secrets-rag.tf` — `athanor-rclone-conf` + `athanor-rag-api-key` in Secret Manager
- [ ] `infra/iam-rag.tf` — SA `athanor-rag-sa`: objectAdmin on both buckets, run.developer, secretAccessor
- [ ] `infra/cloud-run-rag.tf` — athanor-rag service + athanor-ingest job + Cloud Scheduler (europe-west1)

**Validation**: `terraform validate && terraform plan` → 0 errors, ~26 new resources.

### 3f. OpenWebUI Integration

- [ ] `pipelines/pipes/athanor_project.py` — generic Pipe: model name = project name, routes to athanor-rag
- [ ] `pipelines/pipes/ingest_trigger.py` — admin-only Pipe to trigger ingest job from chat
- [ ] Auto-registration: Pipe reads `/api/projects`, creates one OpenWebUI model per project

**Validation**: select project "test" in OpenWebUI → answer with RAG citations.

### 3g. Checkpoint Bidirectional Sync

- [ ] Checkpoint written by ingest: `connector.read_checkpoint()` → GCS `checkpoints/{name}.md`
- [ ] Checkpoint read by RAG service: injected as system context in `/v1/chat/completions`
- [ ] Checkpoint updated by RAG service after conversation: summarize → `POST /api/projects/{name}/checkpoint` → connector.upload_checkpoint() back to Proton Drive

**Validation**: have conversation → close → new conversation on same project → checkpoint context is present.

**Success criteria**: "Retrouve notre contrat d'assurance habitation" works from OpenWebUI. Zero OpenRouter calls from RAG (verified in VertexAI proxy logs). No PDF ever appears in GCS bucket.

**Cost estimate**: ~EUR 2.50/month incremental (athanor-rag 0.50 + ingest job 0.30 + VertexAI embeddings 0.25 + OCR 0.10 + GCS 0.25 + KMS 0.06 + backup 0.10)

---

## Phase 4 — Daily Assistant & Home Automation

### 4a. Daily assistant agents
- [ ] **Email synthesizer** — summarize daily emails (Gmail API or IMAP) into morning briefing
- [ ] **Agenda manager** — parse Google Calendar, suggest daily priorities, detect conflicts
- [ ] **Household task tracker** — recurring tasks, assignments, reminders via OpenWebUI chat

### 4b. Home Assistant integration
- [ ] Home Assistant ↔ OpenWebUI bridge (MCP or custom tool)
- [ ] Voice commands: "Turn off the lights in the kids' rooms"
- [ ] Automation suggestions: "The heating was on while nobody was home for 3 hours"
- [ ] Energy consumption reports via conversational interface

### 4c. Shared project spaces
- [ ] OpenWebUI workspace/channel per family project (e.g., "Dressing project", "Holiday planning")
- [ ] Shared context per project (documents, notes, decisions)
- [ ] Couple-only projects with restricted access

**Success criteria**: Family uses AI daily for practical tasks. Home automation controllable by voice or chat.

---

## Phase 5 — Specialized Domain Agents

### 5a. Home renovation assistant
- [ ] **Architect/renovation agent** — RAG on floor plans, quotes, regulations
- [ ] Budget tracker for renovation projects
- [ ] Planning permit assistant (French urban planning rules)

### 5b. Education & learning
- [ ] **Homework helper agent** — curriculum-aware (French Brevet/Bac), explains step-by-step
- [ ] Flashcard generator from course notes (RAG on teens' documents)
- [ ] Essay reviewer with age-appropriate feedback

**Success criteria**: Agents that understand our specific family data and give actionable, personalized advice.

---

## Phase 6 — Security & Compliance (month 12+)

- [ ] Encrypted RAG pipeline (CMEK + client-side encryption for sensitive docs)
- [ ] Data classification: public / family / sensitive / financial
- [ ] Automatic routing: sensitive → VertexAI only, general → OpenRouter *(RAG already does this from Phase 3)*
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
- [ ] Local face recognition on NUC/RPi5 → export embeddings to GCS → nearest-neighbor in athanor-rag

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
| EU sovereign | No data leaves europe-west9. RAG uses VertexAI only, never OpenRouter |
| No manual deploys | Everything via terraform apply triggered by CI/CD |
| Secrets in Secret Manager | Never in code, env files, or CI logs |
| Observable | Every new service gets cost tracking from day 1 |
| Family-safe | Parental controls on every user-facing feature |
| Corruption-free storage | No SQLite-on-GCS-FUSE for mutable data. ChromaDB loaded in-memory from GCS dumps |
