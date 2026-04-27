# Phase 3 RAG Rules — Athanor

> These rules apply when working on `lib/`, `docker/athanor-rag/`, `docker/athanor-ingest/`, `agents/`, and `infra/*-rag.tf`.
> Full spec: `docs/RAG_IMPLEMENTATION.md` | Plan: `.claude/plans/immutable-crafting-gadget.md`

---

## Core Invariants (NEVER violate)

### 1. No document files on GCS
- Family documents (PDF, DOCX, PPTX, images) are downloaded to `/tmp/ingest/{project}/` and **always** deleted in a `finally` block.
- `shutil.rmtree(tmp_dir)` MUST be in `finally`, not `try`.
- GCS bucket `athanor-ai-rag-data` contains ONLY: `.vectordb/*.json.gz`, `.graphdb/*/`, `checkpoints/*.md`, `manifest.json`.
- If you ever write a PDF/DOCX/image to GCS, you have violated this rule.

### 2. ChromaDB EphemeralClient only
```python
import chromadb
client = chromadb.EphemeralClient()  # CORRECT
# client = chromadb.PersistentClient(path="/data/...")  # NEVER
```
Snapshots are saved/loaded as JSON gzipped via `collection.get(include=["documents","metadatas","embeddings"])`.

### 3. VertexAI Proxy only
- All LLM calls (embeddings, OCR, chat, graph extraction) use `ResilientClient(VERTEXAI_PROXY_URL, VERTEXAI_PROXY_KEY)`.
- No OpenRouter, no direct Gemini API, no Anthropic API in RAG code.
- `VERTEXAI_PROXY_URL` and `VERTEXAI_PROXY_KEY` are the only LLM config accepted.

### 4. rclone.conf security
- The rclone config secret (`athanor-rclone-conf`) is written to `/tmp/rclone.conf` at job start.
- It is deleted at the end of `ingest_job.py` in a top-level `finally`.
- Never pass the rclone config content as a command-line argument (shell history exposure).

---

## Module Responsibilities

| Module | Location | Responsibility |
|---|---|---|
| `DriveConnector` (ABC) | `lib/connectors/base.py` | Interface: list_projects, download, upload checkpoint |
| `ProtonDriveConnector` | `lib/connectors/proton.py` | rclone subprocess, parses `athanor.*` marker YAML |
| `ResilientClient` | `lib/rag_core/client.py` | VertexAI Proxy: chat, chat_multimodal, embed. Retry logic. |
| `EmbeddingClient` | `lib/rag_core/embeddings.py` | Wraps ResilientClient.embed(), batch=100 |
| `VectorStore` | `lib/rag_core/store.py` | EphemeralClient wrapper, save/load GCS json.gz |
| `OcrProcessor` | `lib/rag_core/ocr.py` | Gemini multimodal: render page to 300 DPI PNG, base64, call LLM |
| `parse_document()` | `lib/rag_core/ingest.py` | PDF/DOCX/PPTX/MD/image → list[dict] chunks |
| `KnowledgeGraph` | `lib/rag_core/graph.py` | NetworkX, save/load GCS JSON. Only when graph_enabled=true |
| `TripletExtractor` | `lib/rag_core/graph_extract.py` | Generic: LLM extracts {subject, relation, object} triplets, no pre-defined types |
| `HybridSearcher` | `lib/rag_core/graph_search.py` | Vector search + optional graph traversal |
| `BaseAgent` | `lib/agents/base.py` | Checkpoint injection + RAG context composition |
| `render_system_prompt()` | `lib/agents/template.py` | Fills default.md template with project_name, checkpoint, hint |
| `ingest_job.py` | `docker/athanor-ingest/` | Full ingest flow: discover → download → parse → embed → snapshot → backup |
| FastAPI app | `docker/athanor-rag/` | /health, /api/projects, /api/projects/{name}/search, /v1/chat/completions, /api/reload |

---

## Chunk Format (standardized)

Every parser in `ingest.py` returns chunks in this exact format:
```python
{
    "text": str,           # chunk text content
    "metadata": {
        "source": str,     # original filename (basename only)
        "project": str,    # project name (from marker file suffix)
        "page": int,       # page number (0 if not applicable)
        "chunk_idx": int,  # position in document
        "md5": str,        # MD5 of text content (for deduplication)
        "source_project": str,  # only present when chunk comes from feeds_into
    }
}
```

---

## GCS Snapshot Format

```python
# Save (in VectorStore.save_to_gcs)
data = collection.get(include=["documents", "metadatas", "embeddings"])
json_bytes = json.dumps(data).encode("utf-8")
gz_bytes = gzip.compress(json_bytes)
# Upload to gs://bucket/.vectordb/{project_name}.json.gz

# Load (in VectorStore.load_from_gcs)
gz_bytes = download_from_gcs(bucket, f".vectordb/{project_name}.json.gz")
data = json.loads(gzip.decompress(gz_bytes))
collection.add(
    ids=data["ids"],
    embeddings=data["embeddings"],
    documents=data["documents"],
    metadatas=data["metadatas"],
)
```

---

## Marker File YAML (full format)

```yaml
# athanor.finances  (empty file = all defaults)
description: "Suivi financier et fiscal"
graph_enabled: true          # false by default
feeds_into:
  - immobilier               # chunks also indexed in "immobilier" project
system_prompt_hint: "Cite document sources and dates."
exclude:
  - archives-avant-2020/
```

- Marker file name: `athanor.{project_name}` — suffix = project name = ChromaDB collection = OpenWebUI model
- If file is empty: `project_name` from filename suffix, `graph_enabled=false`, no feeds_into
- Parse with `yaml.safe_load()`, handle empty/None gracefully

---

## feeds_into Implementation

After ingesting a project normally (steps 10-14 in ingest_job.py):
1. Check `project.config.get("feeds_into", [])`.
2. For each `target_name` in the list, check that `target_name` in `manifest`. If not: `log.warning(...)`, skip.
3. Get or create target `VectorStore` from `stores_cache` dict (keyed by project name).
4. Add same chunks with `source_project=project.name` in metadata.
5. After the full project loop: save all `stores_cache` stores to GCS (these are only feeds_into targets — main project stores are saved in step 11).

---

## OCR Trigger

```python
# In parse_document(), per PDF page:
if len(page.get_text().strip()) < 50:
    text = ocr.ocr_page(page)  # Gemini Flash 2.5 multimodal
else:
    text = page.get_text()
```

OCR model is configurable via `OCR_MODEL` env var (default: `gemini-2.5-flash`).
Render at 300 DPI: `fitz.Page.get_pixmap(dpi=300)`.

---

## Ingest Flow (summary, see full spec in RAG_IMPLEMENTATION.md)

```
INIT → read Secret Manager → write /tmp/rclone.conf
DISCOVER → connector.list_projects() → marker files → manifest.json
PER PROJECT (try/finally):
  download to /tmp/ingest/{name}/ → parse → embed → VectorStore.save_to_gcs()
  if graph_enabled: extract triplets (1/5 chunks, max 200) → KnowledgeGraph.save_to_gcs()
  feeds_into → add chunks to target stores_cache
  read checkpoint from Drive → write to GCS checkpoints/{name}.md
  update manifest.json
  finally: shutil.rmtree(/tmp/ingest/{name}/)
POST-LOOP: save all feeds_into target stores (stores_cache)
BACKUP: gcloud storage cp to athanor-ai-rag-backup/{YYYY-MM-DD}/
CLEANUP: os.unlink(/tmp/rclone.conf)
```

---

## Validation Commands (per step)

| Step | Validation |
|---|---|
| Step 1 (connectors/base.py) | `python -c "from lib.connectors.base import DriveConnector, ProjectInfo; print('OK')"` |
| Step 2 (client.py) | `python -c "from lib.rag_core.client import ResilientClient; print('OK')"` |
| Step 3 (store.py) | `python -c "from lib.rag_core.store import VectorStore; print('OK')"` |
| Step 4 (ocr.py) | `python -c "from lib.rag_core.ocr import OcrProcessor; print('OK')"` |
| Step 5 (ingest.py) | `python -c "from lib.rag_core.ingest import parse_document; print('OK')"` |
| Step 6 (graph*.py) | `python -c "from lib.rag_core.graph import KnowledgeGraph; print('OK')"` |
| Step 7 (agents/) | `python -c "from lib.agents.base import BaseAgent; print('OK')"` |
| Step 8 (proton.py) | requires rclone + real Proton Drive + rclone.conf |
| Step 9 (athanor-ingest) | `docker build -t athanor-ingest docker/athanor-ingest/` |
| Step 10 (athanor-rag) | `docker run ... athanor-rag` → `curl /health` → 200 |
| Step 11 (Terraform) | `terraform -chdir=infra validate && terraform plan` → 0 errors |
