 Athanor Projects: Claude Projects-like system backed by Proton Drive

## Context

athanor-ai is a family AI platform on GCP Cloud Run (scale-to-zero, EU-only, ~EUR 30/month). The user wants a system like **Claude Projects** but backed by Proton Drive: tag folders in Proton Drive, auto-discover them, build RAG + GraphRAG per project, and expose each project as a contextual workspace in OpenWebUI with persistent memory via "control points" written back to Proton Drive.

**Concrete example**: Place a file `athanor.roman` in a Proton Drive folder. All folders with this marker become the "Roman" project. A new workspace/model "Roman" appears in OpenWebUI. Conversations are contextual (RAG/GraphRAG). Progress is persisted to Proton Drive as control points, so any new conversation picks up where the last left off.

agent-hub provides a mature RAG stack (ChromaDB, NetworkX GraphRAG, hybrid search, multi-format ingestion, markdown-defined agents, project isolation) that we adapt for this purpose.

---

## Architecture Overview

```
PROTON DRIVE (source of truth)
  /Projets/Roman/
    athanor.roman            ← marker file (project tag)
    notes-recherche.md
    chapitre1-brouillon.docx
    references.pdf
  /Projets/Roman/.athanor/   ← control points (written back by system)
    checkpoint.md            ← latest project state, decisions, progress
    history.jsonl            ← conversation summaries
  /Finance/
    athanor.finance          ← marker file
    releve-2026-03.pdf
    avis-imposition-2025.pdf
  /Finance/.athanor/
    checkpoint.md
    history.jsonl
        │
        │ rclone sync (scheduled)
        ▼
GCS BUCKET (athanor-rag-data)
  /sync/                     ← mirror of Proton Drive tagged folders
        │
        │ Cloud Run Job: athanor-ingest (daily 03:00)
        │   1. Scan /sync/ for athanor.* marker files
        │   2. Per project: parse docs, chunk, embed, extract graph triplets
        │   3. Write ChromaDB collection + NetworkX graph per project
        │   4. Register/update project in manifest.json
        ▼
  /.vectordb/{project}/      ← ChromaDB per project
  /.graphdb/{project}/       ← NetworkX JSON per project
  /manifest.json             ← discovered projects registry
        │
        │ GCS FUSE mount
        ▼
CLOUD RUN SERVICE: athanor-rag (scale-to-zero, 2Gi, 1vCPU)
  FastAPI app
  ├── GET  /health
  ├── GET  /api/projects                    ← list discovered projects
  ├── POST /api/projects/{name}/search      ← RAG hybrid search
  ├── POST /api/projects/{name}/checkpoint  ← write control point
  ├── GET  /api/projects/{name}/checkpoint  ← read latest control point
  └── POST /v1/chat/completions             ← OpenAI-compatible (agent routing)
        │
        │ calls for LLM + embeddings
        ▼
VERTEXAI PROXY (existing, EU-sovereign)
  /v1/chat/completions  (Gemini Pro/Flash)
  /v1/embeddings        (text-embedding)

        ▲
        │ Pipe function per project
OPENWEBUI (existing)
  Model selector shows:
  ├── Gemini 2.5 Flash (existing)
  ├── Gemini 2.5 Pro (existing)
  ├── [Roman]           ← auto-created, RAG-backed
  ├── [Finance]         ← auto-created, RAG-backed
  └── ...
```

---

## Key Design Decisions

### 1. Marker File Convention

**File**: `athanor.{project_name}` (empty file or YAML with optional config)

Placed in any Proton Drive folder. Multiple folders can share the same project tag. The ingestion job discovers all `athanor.*` files recursively, groups folders by project name, and builds one RAG index per project.

**Optional YAML content** (for power users):
```yaml
# athanor.roman
description: "Mon roman en cours d'ecriture"
agent: bookwriter       # which agent definition to use (default: search)
exclude:
  - drafts/old/         # subfolders to skip
```

If the file is empty, defaults apply (project name from filename, `search` agent, no exclusions).

### 2. Per-Project RAG Isolation

Each project gets its own:
- **ChromaDB collection**: `/.vectordb/{project_name}/` on GCS
- **Knowledge graph**: `/.graphdb/{project_name}/` on GCS
- **Control points**: `/sync/{folder}/.athanor/checkpoint.md` (synced back to Proton Drive)

Reuses agent-hub's `VectorStore` (`collection_name` param, `src/rag/store.py:48`) and `KnowledgeGraph` (`persist_dir` param, `src/rag/graph.py:40`).

### 3. Control Points (Persistent Memory)

After each conversation (or periodically), the system writes a **checkpoint** file to the project's `.athanor/` folder:

```markdown
# Roman - Checkpoint
Last updated: 2026-04-08T14:30:00Z

## Current state
- Working on chapter 3, the confrontation scene
- Decided to use first-person narrator (changed from third-person in chapter 2)
- Key character "Marie" introduced in ch2, needs development

## Open questions
- Should the timeline be linear or use flashbacks?
- Research needed: 1920s Paris social customs

## Recent decisions
- 2026-04-08: Changed POV to first person
- 2026-04-05: Settled on 3-act structure
```

This checkpoint is:
- **Injected as system context** at the start of every new conversation on this project
- **Synced back to Proton Drive** via rclone (bidirectional sync on `.athanor/` folders)
- **Updated by the LLM** at the end of conversations (the agent summarizes progress)

Additionally, `history.jsonl` stores conversation summaries (one JSON line per conversation) for longer-term memory.

### 4. OpenWebUI Integration: Pipe Functions as Project Models

Each discovered project becomes a **Pipe function** that appears as a selectable model in OpenWebUI. The Pipe function:

1. Loads the project's checkpoint (persistent context)
2. Performs hybrid RAG search against the project's ChromaDB + graph
3. Composes a system prompt with: agent definition + checkpoint + RAG context
4. Calls Gemini via VertexAI Proxy for the response
5. At conversation end, updates the checkpoint

**Auto-registration**: The athanor-rag service exposes a `/api/projects` endpoint. A **sync Pipe** (installed once in OpenWebUI) periodically checks this endpoint and auto-creates/removes project Pipe functions via OpenWebUI's API:
- `POST /api/v1/knowledge/create` - create knowledge collection
- `POST /api/v1/models/create` - create custom model linked to knowledge + system prompt

### 5. Privacy: All RAG Through VertexAI Only

The athanor-rag service routes ALL LLM calls (including those containing document content) through the existing VertexAI Proxy. **Never through OpenRouter.** Document content stays in GCP europe-west9.

---

## Code Reuse from agent-hub

### Copy into `athanor-ai/lib/rag_core/`

| Source (agent-hub) | Target | Adapt? |
|---|---|---|
| `src/rag/store.py` (355 LOC) | `lib/rag_core/store.py` | Minor: default persist_dir, simplify doc_levels |
| `src/rag/ingest.py` (306 LOC) | `lib/rag_core/ingest.py` | Add: marker file detection, image metadata |
| `src/rag/graph.py` (359 LOC) | `lib/rag_core/graph.py` | As-is (already domain-agnostic) |
| `src/rag/graph_search.py` (~100 LOC) | `lib/rag_core/graph_search.py` | As-is |
| `src/rag/graph_extract.py` (197 LOC) | `lib/rag_core/graph_extract.py` | Change entity types: Person, Document, Account, Property, Institution, Event |
| `src/client.py` (636 LOC) | `lib/rag_core/client.py` | Point at VertexAI Proxy, simplify |

### Copy into `athanor-ai/lib/agents/`

| Source (agent-hub) | Target | Adapt? |
|---|---|---|
| `src/agents/base.py` (274 LOC) | `lib/agents/base.py` | Remove `rich` CLI, add checkpoint injection |
| `src/agent_defs.py` (242 LOC) | `lib/agents/agent_defs.py` | As-is |
| `src/config.py` (175 LOC) | `lib/config.py` | Simplify for family domain |

### New code to write

| File | Purpose |
|---|---|
| `docker/athanor-rag/app.py` | FastAPI app: /health, /api/projects, /api/projects/{name}/search, /v1/chat/completions |
| `docker/athanor-rag/discovery.py` | Scan GCS sync folder for `athanor.*` markers, build project manifest |
| `docker/athanor-rag/checkpoint.py` | Read/write checkpoint files, conversation summary generation |
| `docker/athanor-ingest/ingest_job.py` | Orchestrate: discover markers → parse docs → embed → graph extract → store |
| `pipelines/pipes/athanor_project.py` | OpenWebUI Pipe function: per-project RAG-backed model |
| `agents/defs/search.md` | Default agent: document search with citations |
| `agents/defs/bookwriter.md` | Book writing agent |
| `agents/defs/wealth.md` | Wealth management agent |
| `infra/cloud-run-rag.tf` | Terraform: athanor-rag service + athanor-ingest job |

### Do NOT reuse from agent-hub

- `src/agents/codex.py`, `developer.py`, `specifier.py`, `planner.py`, `presenter.py`, `storyteller.py` (code-specific)
- `synthesize.py`, `watch.py` (code-specific patterns)
- `web/`, `src/mcp_server.py`, `src/workspace_session.py` (replaced by OpenWebUI)
- Cross-encoder reranking (overkill for family-scale corpus)

---

## Terraform Changes

### New: `infra/cloud-run-rag.tf`

```
google_cloud_run_v2_service.athanor_rag
  - image: athanor-rag:latest
  - memory: 2Gi, cpu: 1
  - min_instances: 0, max_instances: 1
  - GCS FUSE volume: athanor-rag-data bucket at /data
  - env: VERTEXAI_PROXY_URL, RAG_API_KEY (from Secret Manager)
  - startup probe: /health, 12 retries x 10s

google_cloud_run_v2_job.athanor_ingest
  - image: athanor-ingest:latest
  - memory: 2Gi, cpu: 1
  - env: same + SYNC_PATH=/data/sync

google_cloud_scheduler_job.athanor_ingest_trigger
  - schedule: "0 3 * * *" (daily 03:00 Europe/Paris)
  - region: europe-west1 (scheduler not available in west9)
```

### New/Modified: `infra/gcs.tf`

```
google_storage_bucket.athanor_rag_data
  - location: europe-west9
  - storage_class: STANDARD
  - versioning: enabled
  - lifecycle: 180-day delete on non-current versions
```

### Modified: `infra/iam.tf`

- Service account for athanor-rag: `storage.objectAdmin` on rag-data bucket
- Secret access for RAG_API_KEY

### Modified: `infra/artifact-registry.tf`

- Cloud Build trigger for `docker/athanor-rag/`
- Cloud Build trigger for `docker/athanor-ingest/`

---

## Cold Start & Cost

| Component | Cold Start | Monthly Cost |
|---|---|---|
| athanor-rag (2Gi, scale-to-zero) | ~15-25s | ~EUR 0.50 (30min/day) |
| athanor-ingest (daily job, ~10min) | N/A (job) | ~EUR 0.30 |
| VertexAI embeddings (incremental) | N/A | ~EUR 0.30 |
| VertexAI Gemini Flash (agents) | N/A | ~EUR 1.00 |
| GCS storage (~6GB) | N/A | ~EUR 0.15 |
| **Total incremental** | | **~EUR 2.25** |

---

## Implementation Roadmap

### Step 1: RAG Core Library (lib/rag_core/)
- Copy and adapt modules from agent-hub
- Adapt graph_extract.py entity types for family documents
- Unit test: ingest a PDF, search, verify results

**Files to create/modify:**
- `athanor-ai/lib/rag_core/__init__.py`
- `athanor-ai/lib/rag_core/store.py` (from agent-hub `src/rag/store.py`)
- `athanor-ai/lib/rag_core/ingest.py` (from agent-hub `src/rag/ingest.py`)
- `athanor-ai/lib/rag_core/graph.py` (from agent-hub `src/rag/graph.py`)
- `athanor-ai/lib/rag_core/graph_search.py` (from agent-hub `src/rag/graph_search.py`)
- `athanor-ai/lib/rag_core/graph_extract.py` (from agent-hub `src/rag/graph_extract.py`)
- `athanor-ai/lib/rag_core/client.py` (from agent-hub `src/client.py`)

### Step 2: Marker Discovery + Ingestion Job
- Write discovery.py: scan for athanor.* files, build manifest
- Write ingest_job.py: orchestrate parse → chunk → embed → graph → store
- Create Docker image for athanor-ingest
- Test locally with sample Proton Drive folder

**Files to create:**
- `athanor-ai/docker/athanor-ingest/Dockerfile`
- `athanor-ai/docker/athanor-ingest/requirements.txt`
- `athanor-ai/docker/athanor-ingest/ingest_job.py`
- `athanor-ai/docker/athanor-ingest/discovery.py`

### Step 3: RAG Service (athanor-rag)
- Write FastAPI app with /health, /api/projects, /api/projects/{name}/search
- Add /v1/chat/completions with agent routing
- Add checkpoint read/write
- Create Docker image
- Test locally: ingest → search → chat

**Files to create:**
- `athanor-ai/docker/athanor-rag/Dockerfile`
- `athanor-ai/docker/athanor-rag/requirements.txt`
- `athanor-ai/docker/athanor-rag/app.py`
- `athanor-ai/docker/athanor-rag/checkpoint.py`
- `athanor-ai/lib/agents/base.py` (from agent-hub `src/agents/base.py`)
- `athanor-ai/lib/agents/agent_defs.py` (from agent-hub `src/agent_defs.py`)
- `athanor-ai/lib/config.py` (from agent-hub `src/config.py`)
- `athanor-ai/agents/defs/search.md`

### Step 4: Terraform + Deploy
- Write infra/cloud-run-rag.tf
- Extend infra/gcs.tf, infra/iam.tf, infra/artifact-registry.tf
- Deploy via CI/CD
- Test end-to-end on GCP

**Files to create/modify:**
- `athanor-ai/infra/cloud-run-rag.tf` (new)
- `athanor-ai/infra/gcs.tf` (modify)
- `athanor-ai/infra/iam.tf` (modify)
- `athanor-ai/infra/artifact-registry.tf` (modify)
- `athanor-ai/infra/variables.tf` (modify)

### Step 5: OpenWebUI Pipe + Auto-Registration
- Write Pipe function that routes to athanor-rag per project
- Auto-create custom models in OpenWebUI for discovered projects
- Test: select "Roman" in model dropdown, ask questions, get RAG-backed answers

**Files to create:**
- `athanor-ai/pipelines/pipes/athanor_project.py`

### Step 6: Control Points + Bidirectional Sync
- Write checkpoint generation (LLM summarizes conversation → markdown)
- Write back to GCS → rclone syncs to Proton Drive
- Test: have conversation, close, open new conversation, verify context persists

**Files to create/modify:**
- `athanor-ai/docker/athanor-rag/checkpoint.py` (extend)
- `athanor-ai/scripts/rclone-sync.sh` (new)

---

## Verification Plan

1. **Marker discovery**: Place `athanor.test` in a GCS folder, run ingestion, verify `manifest.json` lists "test" project
2. **Ingestion**: Upload PDF + DOCX to the folder, run ingestion, verify ChromaDB has chunks and graph has entities
3. **Search**: `curl POST /api/projects/test/search?q=...` returns relevant chunks with scores
4. **Agent chat**: `curl POST /v1/chat/completions` with model="test", verify RAG-augmented response via Gemini
5. **Checkpoint**: Have a conversation, verify `.athanor/checkpoint.md` is written with conversation summary
6. **Continuity**: Start new conversation on same project, verify checkpoint is injected and context is preserved
7. **OpenWebUI**: Select project model in dropdown, chat, verify end-to-end flow
8. **Scale-to-zero**: Wait 15 minutes idle, verify 0 instances, then query and verify cold start works
9. **Privacy**: Check logs to confirm no document content goes through OpenRouter
10. **Multi-project**: Create two projects (roman + finance), verify complete isolation (search in one doesn't return results from the other)