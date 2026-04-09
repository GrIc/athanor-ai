# Integration Architecture: agent-hub RAG & Multi-Agent into athanor-ai
 
## Context
 
athanor-ai is a family AI platform on GCP Cloud Run (scale-to-zero, EU-only, ~EUR30/month budget). It currently runs OpenWebUI + VertexAI Proxy + parental monitoring. The roadmap plans RAG (Phase 4) and specialized agents (Phase 5) but without a concrete implementation path.
 
agent-hub is a mature multi-agent RAG system with ChromaDB vector store, NetworkX knowledge graph, hybrid search, markdown-defined agents, pipeline orchestration, and multi-format document ingestion (PDF/DOCX/PPTX). It was built for codebases but its core RAG and agent framework is domain-agnostic.
 
**Goal**: Leverage agent-hub's RAG stack and agent framework to accelerate athanor-ai's Phase 4-5, enabling personal AI projects (document search, book writing, wealth management, photo analysis, document sorting, etc.) while respecting scale-to-zero, EU sovereignty, cost, and privacy constraints.
 
---
 
## Architecture Decision: Two New Cloud Run Components
 
### Service Topology
 
```
                        OpenWebUI (existing)
                        ├── Pipe functions → call athanor-rag via HTTP
                        ├── Parental Monitor filter (existing)
                        └── Models: OpenRouter + VertexAI proxy (existing)
 
[NEW] athanor-rag       Cloud Run Service (scale-to-zero, 2Gi RAM, 1 vCPU)
                        ├── FastAPI app
                        ├── /v1/chat/completions  (agents as "models")
                        ├── /api/search           (RAG search endpoint)
                        ├── /health
                        ├── ChromaDB (loaded from GCS FUSE)
                        ├── NetworkX graph (loaded from GCS FUSE)
                        └── Calls VertexAI Proxy for embeddings + LLM
 
[NEW] athanor-ingest    Cloud Run Job (scheduled, like weekly-digest pattern)
                        ├── Syncs documents from GCS
                        ├── Parses PDF/DOCX/PPTX/text
                        ├── Chunks → embeds via VertexAI → stores in ChromaDB
                        ├── Extracts knowledge graph triplets
                        └── Writes .vectordb/ and .graphdb/ to GCS
 
Existing (unchanged):
  - athanor-openwebui   Cloud Run Service
  - athanor-vertexai-proxy  Cloud Run Service
  - athanor-weekly-digest   Cloud Run Job
```
 
### Data Flow
 
```
Proton Drive ──rclone──> GCS bucket (athanor-rag-data)
                          /documents/insurance/...
                          /documents/financial/...
                          /documents/school/...
                          /photos/...
                              │
              Cloud Scheduler (daily 03:00)
                              │
                              ▼
                    athanor-ingest Job
                     │  Parse (PyMuPDF, python-docx, python-pptx)
                     │  Chunk (1500 chars / 200 overlap)
                     │  Embed (via VertexAI Proxy /v1/embeddings)
                     │  Extract triplets (via VertexAI Proxy, Gemini Flash)
                     │  Store → .vectordb/ + .graphdb/ on GCS
                              │
                              ▼
                    GCS bucket (athanor-rag-data)
                     /.vectordb/       ← ChromaDB persistent data
                     /.graphdb/        ← NetworkX JSON per project
                     /projects/        ← agent outputs/notes
                              │
                     GCS FUSE mount
                              │
                              ▼
                    athanor-rag Service
                     ← queries from OpenWebUI Pipe functions
                     → RAG search + agent reasoning via Gemini
                     → response back to OpenWebUI
```
 
### Project Namespace Isolation
 
Each use case gets its own ChromaDB collection + graph directory:
 
| Project | Collection | Graph Dir | Content |
|---------|-----------|-----------|---------|
| family-documents | `family-docs` | `.graphdb/family-docs/` | Insurance, school, admin, recipes |
| wealth | `wealth` | `.graphdb/wealth/` | Bank statements, tax, investments |
| book-project | `book` | `.graphdb/book/` | Research notes, references, drafts |
| photos | `photos` | `.graphdb/photos/` | Photo metadata + Gemini descriptions |
 
This uses the existing `collection_name` parameter in `VectorStore.__init__()` (agent-hub `src/rag/store.py:48`).
 
---
 
## Code Reuse Strategy
 
### Copy into `athanor-ai/lib/rag_core/` (adapt as needed)
 
| agent-hub Source | Target | Adaptation |
|---|---|---|
| `src/rag/store.py` | `lib/rag_core/store.py` | Change default persist_dir to `/data/.vectordb`, simplify doc_levels to `document`/`summary`/`metadata` |
| `src/rag/ingest.py` | `lib/rag_core/ingest.py` | Keep PDF/DOCX/PPTX parsers. Remove code-specific binary filters. Add image metadata extraction. |
| `src/rag/graph.py` | `lib/rag_core/graph.py` | As-is (domain-agnostic NetworkX wrapper) |
| `src/rag/graph_search.py` | `lib/rag_core/graph_search.py` | As-is (generic hybrid search logic) |
| `src/rag/graph_extract.py` | `lib/rag_core/graph_extract.py` | Replace code entity types with family types: Person, Document, Account, Property, Institution, Event, Recipe, School |
| `src/client.py` | `lib/rag_core/client.py` | Point base_url at VertexAI Proxy. Simplify retry config. |
| `src/agents/base.py` | `lib/agents/base.py` | Keep RAG context retrieval + system prompt composition. Remove `rich` CLI dependencies. |
| `src/agent_defs.py` | `lib/agents/agent_defs.py` | As-is (markdown agent definition loader) |
| `src/config.py` | `lib/config.py` | Simplify: remove scanning/workspace config, add family-specific domain config |
 
### Do NOT reuse (codebase-specific)
 
- `src/agents/codex.py` - code documentation scanner
- `src/agents/developer.py` - code diff generation
- `src/agents/specifier.py`, `planner.py`, `presenter.py`, `storyteller.py` - software project pipeline
- `watch.py` - file change detection for code workspaces
- `synthesize.py` - code pyramid synthesis (concept useful, implementation code-specific)
- `web/` - agent-hub web UI (OpenWebUI replaces it)
- `src/mcp_server.py` - tool definitions are code-specific (rewrite for family tools)
- `src/workspace_session.py`, `src/reports.py` - code workspace tooling
 
### Simplifications vs agent-hub
 
- **No cross-encoder reranking** - family corpus is small (~50k chunks), cosine similarity suffices
- **No document pyramid synthesis** - flat chunks with `doc_level` metadata by category
- **No inter-agent messaging** (AgentMessenger) - single user, sequential pipeline execution
- **No MCP server** initially - Pipe functions are simpler for OpenWebUI integration
- **No `rich` CLI** - everything through OpenWebUI HTTP API
 
---
 
## New Agent Definitions
 
Create `athanor-ai/agents/defs/` following agent-hub's markdown pattern:
 
### `search.md` - Document Search Agent
- scope: global, model: light (Gemini Flash), temperature: 0.2
- Role: Search family documents, return relevant excerpts with source citations
- Uses RAG: vector search + optional graph traversal
 
### `sorter.md` - Document Classifier Agent
- scope: global, model: light, temperature: 0.1
- Role: Classify documents (insurance/school/medical/financial/admin/recipes/photos/personal)
- Output: JSON with category, date, people, institutions, summary
- Handles French + English documents
 
### `wealth.md` - Wealth Manager Agent
- scope: project (`wealth`), model: heavy (Gemini Pro), temperature: 0.1
- Role: Analyze financial documents, portfolio tracking, tax optimization (French fiscal context)
- RAG over financial documents collection
 
### `bookwriter.md` - Book Writer Agent
- scope: project (`book`), model: heavy, temperature: 0.5
- Role: Based on research notes in RAG, help outline and draft book chapters
- Supports /outline, /draft, /revise commands
 
### `photos.md` - Photo Analyzer Agent
- scope: global, model: heavy (Gemini multimodal), temperature: 0.3
- Role: Describe photos via Gemini Vision, tag people/places/events, store descriptions in RAG
- NOT facial recognition - text-based descriptions only
 
---
 
## OpenWebUI Integration
 
### Method: Pipe Functions (not MCP)
 
Create OpenWebUI Pipe functions (same pattern as `pipelines/filters/parental_monitor.py`) that expose agents as selectable "models" in the OpenWebUI dropdown.
 
Each Pipe function:
1. Receives user message from OpenWebUI
2. Calls `athanor-rag` service at `/v1/chat/completions` with the appropriate agent name
3. Returns the response to OpenWebUI
 
Users see: "Document Search", "Wealth Manager", "Book Writer" etc. as model choices in OpenWebUI.
 
### Privacy Routing
 
**Critical**: RAG queries containing family document content MUST go through VertexAI only (EU-sovereign). The athanor-rag service routes all LLM calls through the existing VertexAI Proxy, never OpenRouter. This aligns with Phase 6 roadmap: "sensitive -> VertexAI only".
 
---
 
## Cold Start Analysis
 
| Component | Load Time | Strategy |
|---|---|---|
| Python + FastAPI | ~3-5s | python:3.12-slim, minimal deps |
| ChromaDB from GCS FUSE | ~5-15s (100k chunks) | Lazy load on first query |
| NetworkX graph | ~1-2s (family scale) | Background thread on startup |
| First VertexAI embedding | ~2-3s (proxy cold start too) | Accept |
| **Total** | **~15-25s** | Startup probe: 12 retries x 10s |
 
Acceptable for a family platform. Scale-to-zero savings far outweigh cold start annoyance.
 
---
 
## Cost Estimate (Incremental Monthly)
 
| Item | EUR/month |
|---|---|
| Cloud Run: athanor-rag (~30min/day active) | ~0.50 |
| Cloud Run: athanor-ingest (~10min/day) | ~0.30 |
| VertexAI embeddings (incremental docs) | ~0.30 |
| VertexAI Gemini Flash (agent interactions) | ~1.00 |
| GCS storage (vectordb + graphdb + docs, ~6GB) | ~0.15 |
| **Total incremental** | **~2.25** |
 
Stays well within the EUR 30/month budget. Existing services use ~EUR 5-10/month.
 
---
 
## Facial Recognition: NOT on Cloud Run
 
Cloud Run has no GPU in europe-west9. CPU-based face detection would be 30+ seconds per image on cold start. Instead:
 
1. **MVP (Phase 4)**: Use Gemini multimodal to describe people in photos ("two girls with brown hair near the front door"). Store descriptions as text in RAG. Not true facial recognition but answers "show me photos of the kids."
2. **Later**: Run face_recognition library on a local device (NUC/RPi5), export embeddings to GCS, do nearest-neighbor matching in athanor-rag.
 
---
 
## Terraform Changes Needed
 
### New file: `infra/cloud-run-rag.tf`
 
Resources:
- `google_cloud_run_v2_service.athanor_rag` - RAG service (2Gi, 1vCPU, scale-to-zero, GCS FUSE mount)
- `google_cloud_run_v2_job.athanor_ingest` - Ingestion job
- `google_cloud_scheduler_job.athanor_ingest_trigger` - Daily at 03:00 Europe/Paris
 
### Modified: `infra/gcs.tf`
 
Add:
- `google_storage_bucket.athanor_rag_data` - Dedicated bucket for vectordb + graphdb + documents
 
### Modified: `infra/iam.tf`
 
Add:
- Secret Manager access for RAG service SA
- GCS access (objectAdmin on rag-data bucket)
- Service-to-service auth (RAG service calls VertexAI Proxy)
 
### Modified: `infra/variables.tf`
 
Add:
- `rag_api_key` (sensitive) - API key for athanor-rag service auth
 
### New: `infra/artifact-registry.tf` (extend)
 
Add Cloud Build triggers for:
- `docker/athanor-rag/Dockerfile`
- `docker/athanor-ingest/Dockerfile`
 
---
 
## Docker Images
 
### `docker/athanor-rag/Dockerfile`
 
```
FROM python:3.12-slim
# FastAPI + ChromaDB + NetworkX + httpx
# Non-root user (UID 1001)
# Health check on /health
```
 
### `docker/athanor-ingest/Dockerfile`
 
```
FROM python:3.12-slim
# PyMuPDF + python-docx + python-pptx + ChromaDB + httpx
# Non-root user (UID 1001)
# CMD: python ingest_job.py
```
 
---
 
## Phased Implementation Roadmap
 
### Phase 2.5 — RAG Infrastructure (2-3 weeks)
1. Copy RAG core modules from agent-hub to `athanor-ai/lib/rag_core/`
2. Adapt `graph_extract.py` entity types for family documents
3. Create `docker/athanor-rag/` with FastAPI app + health endpoint
4. Create `infra/cloud-run-rag.tf` with service + GCS bucket
5. Deploy empty athanor-rag service, verify scale-to-zero
6. Test: upload a PDF to GCS, run ingestion manually, query via curl
 
### Phase 3.0 — Document Ingestion Pipeline (2-3 weeks)
1. Set up rclone Proton Drive → GCS sync (manual first)
2. Create `docker/athanor-ingest/` with ingestion job
3. Adapt ingest.py for family doc types (PDF, DOCX, images)
4. Create Cloud Scheduler trigger (daily 03:00)
5. Test with real family documents
 
### Phase 3.5 — OpenWebUI Integration (1-2 weeks)
1. Create Pipe function: "Document Search" → calls athanor-rag
2. Write `agents/defs/search.md` + `agents/defs/sorter.md`
3. End-to-end test: "Where is our home insurance?" in OpenWebUI
 
### Phase 4.0 — Specialized Agents (2-3 weeks each)
1. Wealth manager agent + financial docs collection
2. Book writer agent + project collection
3. Photo analyzer agent (Gemini multimodal descriptions)
 
### Phase 4.5 — Hardening (1 week)
1. Sensitive doc routing (VertexAI only, never OpenRouter)
2. GCS lifecycle rules for data retention
3. Delete endpoint for GDPR right-to-erasure
4. Cost monitoring for RAG usage
 
---
 
## Verification Plan
 
1. **Infrastructure**: `terraform plan` shows new resources, `terraform apply` deploys successfully
2. **Scale-to-zero**: Service has 0 instances when idle, starts on first request
3. **Ingestion**: Upload test PDF to GCS → run ingest job → verify chunks in ChromaDB
4. **Search**: curl athanor-rag `/api/search?q=insurance` returns relevant chunks
5. **Agent**: curl athanor-rag `/v1/chat/completions` with agent name, get RAG-augmented response
6. **OpenWebUI**: Select "Document Search" model, ask a question, get answer citing family docs
7. **Privacy**: Verify no document content leaves EU (check VertexAI proxy logs, no OpenRouter calls from RAG)
8. **Cost**: Monitor GCP billing for 1 week, confirm < EUR 5/month incremental