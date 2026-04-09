# RAG Implementation Spec — Phase 3 (athanor-rag + athanor-ingest)

> **Authoritative implementation guide for Phase 3.**
> Written for autonomous coding agents (Roo Code, Claude Code): every decision is pre-made, every path is explicit.
> Last updated: 2026-04-09
>
> Supersedes the previous version (Proton Drive via GCS sync). The new architecture uses ephemeral file downloads: documents are never stored on GCS.

---

## Implementation Order

Execute steps in order. Each step has a validation command. Do not proceed to the next step until validation passes.

| Step | What to build | Validation |
|------|---------------|------------|
| 1 | `lib/connectors/base.py` | `python -c "from lib.connectors.base import DriveConnector, ProjectInfo; print('OK')"` |
| 2 | `lib/rag_core/client.py` + `lib/rag_core/embeddings.py` | `python -c "from lib.rag_core.client import ResilientClient; print('OK')"` |
| 3 | `lib/rag_core/store.py` | `python -c "from lib.rag_core.store import VectorStore; print('OK')"` |
| 4 | `lib/rag_core/ocr.py` | `python -c "from lib.rag_core.ocr import OcrProcessor; print('OK')"` |
| 5 | `lib/rag_core/ingest.py` | Import check + parse one local PDF without VertexAI |
| 6 | `lib/rag_core/graph*.py` (graph.py, graph_extract.py, graph_search.py) | `python -c "from lib.rag_core.graph import KnowledgeGraph; print('OK')"` |
| 7 | `lib/agents/base.py` + `lib/agents/template.py` + `agents/defs/default.md` | `python -c "from lib.agents.base import BaseAgent; print('OK')"` |
| 8 | `lib/connectors/proton.py` | Manual test with local rclone.conf |
| 9 | `docker/athanor-ingest/` (Dockerfile + ingest_job.py) | `docker build -t athanor-ingest docker/athanor-ingest/` |
| 10 | `docker/athanor-rag/` (FastAPI + routes) | `docker run ... athanor-rag` → `curl /health` → 200 |
| 11 | Terraform (kms-rag.tf, gcs-rag.tf, iam-rag.tf, secrets-rag.tf, cloud-run-rag.tf) | `terraform -chdir=infra validate && terraform plan` → 0 errors |
| 12 | End-to-end GCP test | marker in Proton Drive → run job → curl search → no PDF on GCS |
| 13 | `pipelines/pipes/athanor_project.py` + `pipelines/pipes/ingest_trigger.py` | OpenWebUI: select project → RAG response |
| 14 | Checkpoint bidirectional (extend ingest + checkpoint.py in RAG service) | Proton Drive has `.athanor/checkpoint.md` after ingest |

---

## Critical Invariants (NEVER violate)

1. **No family documents on GCS** — GCS bucket contains only: `.vectordb/`, `.graphdb/`, `checkpoints/`, `manifest.json`. Documents are downloaded to `/tmp/ingest/{project}/` and deleted in a `finally` block.
2. **ChromaDB = EphemeralClient only** — Never `PersistentClient`. Never SQLite on GCS FUSE (known corruption risk).
3. **All LLM calls via VertexAI Proxy** — No OpenRouter key in RAG service config. No exceptions.
4. **Snapshot format** = `collection.get(include=["documents","metadatas","embeddings"])` → JSON → gzip → GCS. Not the native ChromaDB export format.

---

## Architecture Overview

```
PROTON DRIVE
  /Finances/
    athanor.finances          ← marker file (project tag)
    releve-2026-03.pdf
    avis-imposition.pdf
  /Finances/.athanor/
    checkpoint.md             ← written back by ingest job
  /Immobilier/
    athanor.immobilier
    compromis-vente.pdf
        │
        │ rclone (in-memory, ephemeral)
        ▼
INGEST JOB (Cloud Run Job, daily 03:00)
  /tmp/ingest/{project}/      ← deleted in finally
        │
        │ embed + extract
        ▼
GCS: athanor-ai-rag-data/
  .vectordb/{project}.json.gz
  .graphdb/{project}/knowledge_graph.json
  checkpoints/{project}.md
  manifest.json
        │
        │ load at startup
        ▼
RAG SERVICE (Cloud Run, scale-to-zero)
  FastAPI — in-memory ChromaDB
        │
        │ Pipe function per project
        ▼
OPENWEBUI — "finances", "immobilier" models
```

---

## GCS Bucket Structure

```
gs://athanor-ai-rag-data/          ← Standard, CMEK, NO DOCUMENTS EVER
  .vectordb/{project}.json.gz      ← ChromaDB snapshot (json+gzip)
  .graphdb/{project}/
    knowledge_graph.json           ← NetworkX (only if graph_enabled: true)
  checkpoints/{project}.md         ← Latest control point (mirrored from Proton Drive)
  manifest.json                    ← Project registry

gs://athanor-ai-rag-backup/        ← Nearline, CMEK, lifecycle: 90-day delete
  {YYYY-MM-DD}/
    .vectordb/
    .graphdb/
    manifest.json
```

---

## Marker File Format

Placed by the user in any Proton Drive folder. Filename: `athanor.{project_name}`.
Content is optional YAML. Empty file = all defaults.

```yaml
# athanor.finances
description: "Suivi financier et fiscal"
graph_enabled: true          # default: false
feeds_into:
  - immobilier               # unidirectional: finances docs also ingested into immobilier
system_prompt_hint: "Cite les documents sources et les dates."
exclude:
  - archives-avant-2020/
```

`feeds_into` means: after ingesting this project, inject its chunks/triplets into the target project's collection too. The target project must have its own `athanor.$TARGET` marker.

---

## File Structure

```
athanor-ai/
├── lib/
│   ├── connectors/
│   │   ├── __init__.py          ← get_connector() factory (proton only)
│   │   ├── base.py              ← DriveConnector ABC + ProjectInfo + ConnectorError
│   │   └── proton.py            ← ProtonDriveConnector (rclone subprocess)
│   ├── rag_core/
│   │   ├── __init__.py
│   │   ├── client.py            ← ResilientClient (OpenAI-compatible, VertexAI Proxy)
│   │   ├── embeddings.py        ← EmbeddingClient (batched, via ResilientClient)
│   │   ├── store.py             ← VectorStore: EphemeralClient + save/load GCS (json.gz)
│   │   ├── ocr.py               ← OcrProcessor: Gemini multimodal via VertexAI Proxy
│   │   ├── ingest.py            ← parse_document(): PDF+OCR / DOCX / PPTX / images / MD
│   │   ├── graph.py             ← KnowledgeGraph (NetworkX) + save/load GCS
│   │   ├── graph_extract.py     ← TripletExtractor: generic LLM-based extraction
│   │   └── graph_search.py      ← HybridSearcher: vector + graph traversal
│   └── agents/
│       ├── __init__.py
│       ├── base.py              ← BaseAgent: checkpoint injection + RAG search
│       └── template.py          ← render_system_prompt(project_name, checkpoint, hint)
├── agents/
│   └── defs/
│       └── default.md           ← Single generic agent template
├── docker/
│   ├── athanor-rag/
│   │   ├── Dockerfile           ← python:3.12-slim (no rclone, no tesseract)
│   │   ├── requirements.txt
│   │   ├── main.py              ← FastAPI app + lifespan (load snapshots at startup)
│   │   └── routes/
│   │       ├── health.py        ← GET /health (list projects + chunk counts)
│   │       ├── projects.py      ← GET /api/projects
│   │       ├── search.py        ← POST /api/projects/{name}/search
│   │       ├── chat.py          ← POST /v1/chat/completions (model field = project name)
│   │       ├── checkpoint.py    ← GET/POST /api/projects/{name}/checkpoint
│   │       └── admin.py         ← POST /api/reload, POST /ingest/trigger
│   └── athanor-ingest/
│       ├── Dockerfile           ← python:3.12-slim + rclone (apt), no tesseract
│       ├── requirements.txt
│       └── ingest_job.py        ← Full ingest flow (see below)
├── pipelines/
│   └── pipes/
│       ├── athanor_project.py   ← OpenWebUI Pipe: routes to athanor-rag by project name
│       └── ingest_trigger.py    ← OpenWebUI admin Pipe: trigger ingest from chat
├── infra/
│   ├── kms-rag.tf               ← NEW: Cloud KMS keyring + key (europe-west9, 90-day rotation)
│   ├── gcs-rag.tf               ← NEW: 2 buckets (rag-data Standard + rag-backup Nearline, CMEK)
│   ├── iam-rag.tf               ← NEW: service account athanor-rag-sa + bindings
│   ├── secrets-rag.tf           ← NEW: athanor-rclone-conf + athanor-rag-api-key secrets
│   └── cloud-run-rag.tf         ← NEW: RAG service + ingest job + Cloud Scheduler
└── docs/
    ├── RAG_IMPLEMENTATION.md    ← This file
    └── CONNECTORS.md            ← DriveConnector interface + rclone setup guide
```

---

## Step 1: lib/connectors/base.py

```python
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional


class ConnectorError(Exception):
    pass


@dataclass
class ProjectInfo:
    name: str                        # suffix from athanor.{name}
    source_paths: list[str]          # Proton Drive folder paths containing the marker
    config: dict = field(default_factory=dict)  # parsed YAML from marker file (optional)
    marker_mtime: Optional[str] = None          # ISO8601, for incremental ingest


class DriveConnector(ABC):
    @abstractmethod
    def list_projects(self) -> list[ProjectInfo]:
        """Scan for athanor.* marker files. Returns one ProjectInfo per unique project name."""

    @abstractmethod
    def download_project_files(self, project: ProjectInfo, dest_path: Path) -> list[Path]:
        """
        Download all files from project source_paths to dest_path.
        Excludes: .athanor/**, athanor.*, files > 50MB.
        Returns list of downloaded file paths.
        """

    @abstractmethod
    def delete_temp_files(self, dest_path: Path) -> None:
        """shutil.rmtree(dest_path). Called in finally block — always runs."""

    @abstractmethod
    def upload_checkpoint(self, project_name: str, source_folder: str, content: str) -> None:
        """Write content to {source_folder}/.athanor/checkpoint.md on Drive."""

    @abstractmethod
    def read_checkpoint(self, project_name: str) -> Optional[str]:
        """Read {source_folder}/.athanor/checkpoint.md. Returns None if not found."""
```

Also create `lib/connectors/__init__.py`:
```python
import os
from lib.connectors.base import DriveConnector


def get_connector(connector_type: str | None = None, **kwargs) -> DriveConnector:
    t = connector_type or os.getenv("CONNECTOR_TYPE", "proton")
    if t == "proton":
        from lib.connectors.proton import ProtonDriveConnector
        return ProtonDriveConnector(**kwargs)
    raise ValueError(f"Unknown connector type: {t}. Supported: proton")
```

---

## Step 2: lib/rag_core/client.py + embeddings.py

### client.py

Copied and adapted from `agent-hub/src/client.py`. Key changes:
- Remove all references to `os.getenv("API_KEY")` / `os.getenv("API_BASE_URL")` — use `VERTEXAI_PROXY_URL` and `VERTEXAI_PROXY_KEY`
- Remove `rerank()` method (not used)
- Remove `chat_stream()` or keep it — it will be used by the RAG service for streaming responses
- Keep `_is_retryable`, `_format_error`, `chat()`, `embed()` with retry logic intact

Constructor signature:
```python
class ResilientClient:
    def __init__(
        self,
        api_key: str,        # VERTEXAI_PROXY_KEY (from Secret Manager)
        base_url: str,       # VERTEXAI_PROXY_URL (env var)
        max_retries: int = 8,
        timeout: float = 180.0,
    ): ...
```

Also add `chat_multimodal()` method for OCR (sends image as base64 in the message):
```python
def chat_multimodal(self, model: str, text_prompt: str, image_b64: str, image_mime: str = "image/png") -> str:
    """Send a multimodal message (text + image). Returns text response."""
    messages = [{
        "role": "user",
        "content": [
            {"type": "text", "text": text_prompt},
            {"type": "image_url", "image_url": {"url": f"data:{image_mime};base64,{image_b64}"}},
        ]
    }]
    return self.chat(messages=messages, model=model, temperature=0.0, max_tokens=4096)
```

### embeddings.py

```python
class EmbeddingClient:
    def __init__(self, client: ResilientClient, model: str):
        self.client = client
        self.model = model  # from EMBED_MODEL env var

    def embed_batch(self, texts: list[str], batch_size: int = 100) -> list[list[float]]:
        """Embed texts in batches. Returns list of embedding vectors."""
        all_embeddings = []
        for i in range(0, len(texts), batch_size):
            batch = texts[i:i + batch_size]
            embeddings = self.client.embed(batch, model=self.model)
            all_embeddings.extend(embeddings)
        return all_embeddings
```

---

## Step 3: lib/rag_core/store.py

Uses `chromadb.EphemeralClient()` (in-memory). Never `PersistentClient`.

```python
import json, gzip
from google.cloud import storage


class VectorStore:
    def __init__(self, project_name: str):
        import chromadb
        self._client = chromadb.EphemeralClient()
        self._collection = self._client.get_or_create_collection(
            name=project_name,
            metadata={"hnsw:space": "cosine"},
        )
        self.project_name = project_name

    def add_chunks(self, chunks: list[dict], embeddings: list[list[float]]) -> int:
        """
        Add pre-embedded chunks to the collection.
        chunks: list of {text, source, chunk_index, metadata: dict}
        embeddings: parallel list of embedding vectors
        Deduplicates by MD5 of text.
        """

    def search(self, query_embedding: list[float], top_k: int = 8) -> list[dict]:
        """Returns list of {text, source, score, metadata}."""

    def save_to_gcs(self, bucket_name: str, project_name: str) -> None:
        """
        Serialize collection via collection.get(include=["documents","metadatas","embeddings"])
        → JSON → gzip → upload to gs://{bucket}/.vectordb/{project}.json.gz
        """
        data = self._collection.get(include=["documents", "metadatas", "embeddings"])
        serialized = json.dumps(data).encode()
        compressed = gzip.compress(serialized)
        gcs = storage.Client()
        bucket = gcs.bucket(bucket_name)
        blob = bucket.blob(f".vectordb/{project_name}.json.gz")
        blob.upload_from_string(compressed, content_type="application/gzip")

    @classmethod
    def load_from_gcs(cls, bucket_name: str, project_name: str) -> "VectorStore":
        """
        Download gs://{bucket}/.vectordb/{project}.json.gz → decompress → load into EphemeralClient.
        Returns loaded VectorStore instance.
        """
        gcs = storage.Client()
        bucket = gcs.bucket(bucket_name)
        blob = bucket.blob(f".vectordb/{project_name}.json.gz")
        compressed = blob.download_as_bytes()
        data = json.loads(gzip.decompress(compressed))
        store = cls(project_name)
        if data.get("ids"):
            store._collection.add(
                ids=data["ids"],
                documents=data["documents"],
                metadatas=data["metadatas"],
                embeddings=data["embeddings"],
            )
        return store

    @property
    def count(self) -> int:
        return self._collection.count()
```

---

## Step 4: lib/rag_core/ocr.py

```python
import base64
import fitz  # PyMuPDF


OCR_THRESHOLD_CHARS = 50  # pages with fewer native chars trigger OCR


class OcrProcessor:
    def __init__(self, client: "ResilientClient", model: str):
        """
        client: ResilientClient pointing to VertexAI Proxy
        model: e.g. "gemini-2.5-flash" (from OCR_MODEL env var)
        """
        self.client = client
        self.model = model

    def ocr_page(self, page: fitz.Page) -> str:
        """
        If page has enough native text, return it directly.
        Otherwise: render at 300 DPI → PNG → base64 → Gemini multimodal call.
        """
        native_text = page.get_text().strip()
        if len(native_text) >= OCR_THRESHOLD_CHARS:
            return native_text

        # Render page to PNG at 300 DPI
        mat = fitz.Matrix(300/72, 300/72)
        pix = page.get_pixmap(matrix=mat)
        png_bytes = pix.tobytes("png")
        b64 = base64.b64encode(png_bytes).decode()

        prompt = (
            "Transcris le texte de cette image exactement, en conservant la mise en forme. "
            "Retourne uniquement le texte, sans commentaires."
        )
        return self.client.chat_multimodal(
            model=self.model,
            text_prompt=prompt,
            image_b64=b64,
            image_mime="image/png",
        )

    def ocr_image(self, path: "Path") -> str:
        """OCR a standalone image file (JPG, PNG, etc.)."""
        with open(path, "rb") as f:
            b64 = base64.b64encode(f.read()).decode()
        suffix = path.suffix.lower().lstrip(".")
        mime_map = {"jpg": "image/jpeg", "jpeg": "image/jpeg", "png": "image/png", "webp": "image/webp"}
        mime = mime_map.get(suffix, "image/jpeg")
        prompt = "Transcris le texte de cette image exactement. Retourne uniquement le texte."
        return self.client.chat_multimodal(model=self.model, text_prompt=prompt, image_b64=b64, image_mime=mime)
```

---

## Step 5: lib/rag_core/ingest.py

`parse_document(file: Path, collection: str, ocr: OcrProcessor) -> list[dict]`

Returns a list of chunk dicts: `{text, source, chunk_index, metadata: {collection, file_type, ...}}`.

Supported formats:
- **PDF** (`.pdf`): PyMuPDF (`fitz`). Per page: extract native text. If `len(text.strip()) < 50` → `ocr.ocr_page(page)`. Chunk at ~500 tokens (≈2000 chars) with 200 char overlap.
- **DOCX** (`.docx`): `python-docx`. Extract paragraphs. Chunk the same way.
- **PPTX** (`.pptx`): `python-pptx`. Extract text from each slide's shapes.
- **Markdown / TXT** (`.md`, `.txt`): Read as plain text. Chunk.
- **Images** (`.jpg`, `.jpeg`, `.png`, `.webp`): `ocr.ocr_image(file)` → one chunk.
- Other extensions: skip with a warning log.

Chunking: simple fixed-size with overlap. No sentence-level splitting needed at this scale.

```python
def parse_document(file: Path, collection: str, ocr: OcrProcessor) -> list[dict]:
    ...

def _chunk_text(text: str, source: str, collection: str,
                chunk_size: int = 2000, overlap: int = 200) -> list[dict]:
    ...
```

---

## Step 6: lib/rag_core/graph*.py

### graph.py — KnowledgeGraph

```python
import json
import networkx as nx
from google.cloud import storage


class KnowledgeGraph:
    def __init__(self):
        self.graph = nx.DiGraph()

    def add_triplets(self, triplets: list[dict]) -> None:
        """Add {subject, relation, object} triplets to the graph."""
        for t in triplets:
            self.graph.add_edge(t["subject"], t["object"], relation=t["relation"])

    def neighbors(self, entity: str, max_hops: int = 2) -> list[str]:
        """BFS from entity up to max_hops. Returns list of related entity names."""

    def save_to_gcs(self, bucket_name: str, project_name: str) -> None:
        """Serialize with nx.node_link_data() → JSON → GCS .graphdb/{project}/knowledge_graph.json"""

    @classmethod
    def load_from_gcs(cls, bucket_name: str, project_name: str) -> "KnowledgeGraph":
        """Download and deserialize."""

    @property
    def node_count(self) -> int:
        return self.graph.number_of_nodes()
```

### graph_extract.py — TripletExtractor

Generic: LLM discovers entities and relations freely, no pre-defined types.

```python
import json


EXTRACT_PROMPT = """Extrait toutes les entités nommées et leurs relations présentes dans ce texte.
Pour chaque triplet, retourne: {"subject": "...", "relation": "...", "object": "..."}
Sois exhaustif. Les noms d'entités doivent être normalisés (même casse, même forme).
Retourne uniquement un JSON array de triplets, sans commentaires."""


class TripletExtractor:
    def __init__(self, client: "ResilientClient", model: str):
        self.client = client
        self.model = model  # same as chat model (e.g. gemini-2.5-flash)

    def extract_from_text(self, text: str) -> list[dict]:
        """Returns list of {subject, relation, object} dicts. Returns [] on parse error."""
        messages = [
            {"role": "system", "content": EXTRACT_PROMPT},
            {"role": "user", "content": text[:3000]},  # truncate to avoid token waste
        ]
        try:
            raw = self.client.chat(messages=messages, model=self.model,
                                   temperature=0.0, max_tokens=2048)
            return json.loads(raw)
        except Exception:
            return []
```

### graph_search.py — HybridSearcher

Combines vector search results with graph traversal:
1. Run vector search → get top_k results
2. Extract entity names from query (simple NER or keyword match against graph nodes)
3. For each entity found in graph: BFS 2 hops → collect neighbors
4. Boost chunks that mention these neighbors (source file overlap)

```python
class HybridSearcher:
    def __init__(self, store: "VectorStore", graph: KnowledgeGraph,
                 max_hops: int = 2, graph_boost: float = 0.3):
        ...

    def search(self, query: str, query_embedding: list[float], top_k: int = 8) -> list[dict]:
        ...
```

---

## Step 7: lib/agents/base.py + template.py + agents/defs/default.md

### template.py

```python
def render_system_prompt(project_name: str, checkpoint: str | None, hint: str | None) -> str:
    """Build system prompt from generic template + project-specific context."""
    checkpoint_section = f"\n## Current project state\n{checkpoint}" if checkpoint else ""
    hint_section = f"\n{hint}" if hint else ""
    return f"""Tu es un assistant spécialisé sur le projet "{project_name}".
Tu as accès à tous les documents indexés de ce projet.
{checkpoint_section}
Cite tes sources (nom de fichier + extrait) quand tu réponds.{hint_section}"""
```

### base.py

```python
class BaseAgent:
    def __init__(self, project_name: str, store: "VectorStore",
                 client: "ResilientClient", embed_client: "EmbeddingClient",
                 checkpoint: str | None = None,
                 system_prompt_hint: str | None = None,
                 chat_model: str = "gemini-2.5-flash"):
        self.project_name = project_name
        self.store = store
        self.client = client
        self.embed_client = embed_client
        self.checkpoint = checkpoint
        self.chat_model = chat_model
        self.system_prompt = render_system_prompt(project_name, checkpoint, system_prompt_hint)

    def answer(self, user_message: str, history: list[dict] | None = None) -> str:
        """
        1. Embed user_message
        2. Search store → top 5 chunks
        3. Build messages: system_prompt + RAG context + history + user_message
        4. Call client.chat()
        """
```

### agents/defs/default.md

```markdown
# Default Agent

Generic project assistant. Answers questions using indexed documents.
Cites sources (filename + excerpt) for every claim.
If information is not found in the documents, says so explicitly.
Language: responds in the same language as the user's question.
```

---

## Step 8: lib/connectors/proton.py

Uses `rclone` as a subprocess. rclone.conf is stored in Secret Manager, written to `/tmp/rclone.conf` at job startup, deleted at end.

```python
import subprocess, shutil, yaml
from pathlib import Path
from lib.connectors.base import DriveConnector, ProjectInfo, ConnectorError


class ProtonDriveConnector(DriveConnector):
    def __init__(self, rclone_conf: str, remote_name: str = "proton",
                 drive_root: str = "/"):
        """
        rclone_conf: path to rclone.conf on disk (e.g. "/tmp/rclone.conf")
        remote_name: rclone remote name as defined in rclone.conf
        drive_root: root path on Proton Drive to scan (default: "/")
        """
        self.rclone_conf = rclone_conf
        self.remote = remote_name
        self.root = drive_root.rstrip("/")

    def _rclone(self, args: list[str]) -> subprocess.CompletedProcess:
        cmd = ["rclone", "--config", self.rclone_conf] + args
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode != 0:
            raise ConnectorError(f"rclone failed: {result.stderr}")
        return result

    def list_projects(self) -> list[ProjectInfo]:
        """
        rclone lsf --recursive --include "athanor.*" --exclude ".athanor/**"
        Groups results by project name (suffix after 'athanor.').
        Reads YAML content if marker file is not empty.
        """

    def download_project_files(self, project: ProjectInfo, dest_path: Path) -> list[Path]:
        """
        For each source_path in project.source_paths:
          rclone copy --exclude ".athanor/**" --exclude "athanor.*" --max-size 50M
        """

    def delete_temp_files(self, dest_path: Path) -> None:
        shutil.rmtree(dest_path, ignore_errors=True)

    def upload_checkpoint(self, project_name: str, source_folder: str, content: str) -> None:
        """Write content to a temp file, then rclone copyto to {source_folder}/.athanor/checkpoint.md"""

    def read_checkpoint(self, project_name: str) -> str | None:
        """rclone cat {source_folder}/.athanor/checkpoint.md → return content or None"""
```

---

## Step 9: docker/athanor-ingest/ingest_job.py

Full ingest flow. Entry point is `python ingest_job.py`.

```
ENV VARS (all required unless noted):
  CONNECTOR_TYPE=proton
  PROTON_DRIVE_ROOT=/
  RCLONE_CONFIG_SECRET=athanor-rclone-conf   ← Secret Manager secret name
  RAG_GCS_BUCKET=athanor-ai-rag-data
  RAG_GCS_BACKUP_BUCKET=athanor-ai-rag-backup
  VERTEXAI_PROXY_URL=https://...
  VERTEXAI_PROXY_KEY=...                      ← from Secret Manager
  OCR_MODEL=gemini-2.5-flash
  EMBED_MODEL=text-multilingual-embedding-002
  GCP_PROJECT_ID=athanor-ai
  GCP_REGION=europe-west9
```

```python
# Pseudocode for ingest_job.py

def main():
    # INIT
    # 1. Fetch rclone.conf from Secret Manager → write to /tmp/rclone.conf
    # 2. connector = get_connector("proton", rclone_conf="/tmp/rclone.conf", drive_root=PROTON_DRIVE_ROOT)
    # 3. gemini_client = ResilientClient(api_key=VERTEXAI_PROXY_KEY, base_url=VERTEXAI_PROXY_URL)
    # 4. embed_client = EmbeddingClient(gemini_client, model=EMBED_MODEL)
    # 5. ocr = OcrProcessor(client=gemini_client, model=OCR_MODEL)

    # DISCOVERY
    # 6. projects = connector.list_projects()
    # 7. Load existing manifest.json from GCS (or empty dict)
    # 8. Update manifest with discovered projects

    stores_cache = {}   # {project_name: VectorStore} — for feeds_into targets
    graphs_cache = {}   # {project_name: KnowledgeGraph} — for feeds_into targets
    succeeded = 0

    # PER PROJECT LOOP
    for project in projects:
        tmp_dir = Path(f"/tmp/ingest/{project.name}")
        tmp_dir.mkdir(parents=True, exist_ok=True)
        try:
            # 9. files = connector.download_project_files(project, tmp_dir)
            # 10. all_chunks = []
            #     for file in files:
            #       all_chunks.extend(parse_document(file, project.name, ocr))
            # 11. embeddings = embed_client.embed_batch([c["text"] for c in all_chunks])
            #     store = VectorStore(project.name)
            #     store.add_chunks(all_chunks, embeddings)
            #     store.save_to_gcs(RAG_GCS_BUCKET, project.name)
            # 12. if project.config.get("graph_enabled"):
            #       graph = KnowledgeGraph()
            #       extractor = TripletExtractor(gemini_client, model=CHAT_MODEL)
            #       for chunk in all_chunks[::5][:200]:  # 1 in 5, max 200
            #           graph.add_triplets(extractor.extract_from_text(chunk["text"]))
            #       graph.save_to_gcs(RAG_GCS_BUCKET, project.name)

            # FEEDS_INTO
            # 13. for target_name in project.config.get("feeds_into", []):
            #       if target_name not in manifest: log.warning; continue
            #       target_store = stores_cache.setdefault(target_name, VectorStore(target_name))
            #       enriched = [{**c, "metadata": {**c["metadata"], "source_project": project.name}}
            #                   for c in all_chunks]
            #       target_store.add_chunks(enriched, embeddings)
            #       if manifest.get(target_name, {}).get("graph_enabled") and project.config.get("graph_enabled"):
            #           target_graph = graphs_cache.setdefault(target_name, KnowledgeGraph())
            #           target_graph.add_triplets(triplets)  # triplets from step 12

            # 14. checkpoint = connector.read_checkpoint(project.name)
            #     gcs_write(RAG_GCS_BUCKET, f"checkpoints/{project.name}.md", checkpoint or "")
            # 15. manifest[project.name] = {updated_at, chunk_count, graph_enabled, feeds_into, system_prompt_hint}
            #     gcs_write(RAG_GCS_BUCKET, "manifest.json", json.dumps(manifest))

            succeeded += 1

        except Exception as e:
            log.error(f"Project {project.name} failed: {e}")
        finally:
            # 16. connector.delete_temp_files(tmp_dir)  ← ALWAYS runs
            pass

    # POST-LOOP: save feeds_into target stores (not the main project stores, already saved)
    # 17. for target_name, target_store in stores_cache.items():
    #       target_store.save_to_gcs(RAG_GCS_BUCKET, target_name)
    #     for target_name, target_graph in graphs_cache.items():
    #       target_graph.save_to_gcs(RAG_GCS_BUCKET, target_name)

    # BACKUP
    if succeeded > 0:
        # 18. date_prefix = datetime.utcnow().strftime("%Y-%m-%d")
        #     subprocess.run(["gcloud", "storage", "cp", "-r",
        #       f"gs://{RAG_GCS_BUCKET}/.vectordb/",
        #       f"gs://{RAG_GCS_BACKUP_BUCKET}/{date_prefix}/.vectordb/"])
        #     (same for .graphdb/ and manifest.json)
        pass

    # CLEANUP
    # 19. os.unlink("/tmp/rclone.conf")
    # 20. sys.exit(0 if succeeded > 0 else 1)
```

### docker/athanor-ingest/Dockerfile

```dockerfile
FROM python:3.12-slim

# Install rclone (for Proton Drive connector)
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl unzip \
    && curl https://rclone.org/install.sh | bash \
    && apt-get clean && rm -rf /var/lib/apt/lists/*

# Non-root user
RUN useradd -m -u 1001 ingest
USER 1001
WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY --chown=ingest:ingest . .
# lib/ is mounted or copied at build time
COPY --chown=ingest:ingest ../../lib ./lib

CMD ["python", "ingest_job.py"]
```

### docker/athanor-ingest/requirements.txt

```
chromadb>=0.5
openai>=1.0
httpx>=0.27
google-cloud-storage>=2.14
google-cloud-secret-manager>=2.20
PyMuPDF>=1.24
python-docx>=1.1
python-pptx>=0.6
Pillow>=10.0
networkx>=3.2
pyyaml>=6.0
```

---

## Step 10: docker/athanor-rag/ (FastAPI)

### main.py — lifespan

```python
from contextlib import asynccontextmanager
from fastapi import FastAPI

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Load all project snapshots from GCS at startup
    app.state.stores = {}      # {project_name: VectorStore}
    app.state.graphs = {}      # {project_name: KnowledgeGraph}
    app.state.manifest = {}    # {project_name: dict}
    await load_all_projects(app)
    yield
    # Cleanup if needed

app = FastAPI(lifespan=lifespan)
```

`load_all_projects()`:
1. Download `manifest.json` from GCS
2. For each project in manifest: `VectorStore.load_from_gcs()` + (if graph_enabled) `KnowledgeGraph.load_from_gcs()`

### routes/health.py

`GET /health` → returns `{"status": "ok", "projects": {"finances": {"chunks": 1234, "graph_nodes": 0}}}`

### routes/projects.py

`GET /api/projects` → returns manifest.json content

### routes/search.py

`POST /api/projects/{name}/search`
Body: `{"query": str, "top_k": int = 8}`
Returns: `{"results": [{text, source, score}]}`

### routes/chat.py

`POST /v1/chat/completions`
OpenAI-compatible. `model` field contains project name (e.g. `"finances"`).
- Extracts last user message
- Embeds it → searches project store
- Builds prompt with system_prompt + RAG context + conversation history
- Calls VertexAI Proxy for response
- Supports streaming if `stream: true`

### routes/checkpoint.py

`GET /api/projects/{name}/checkpoint` → returns checkpoint.md content from GCS
`POST /api/projects/{name}/checkpoint` → writes new checkpoint to GCS (and calls connector to push to Proton Drive — FUTURE: step 14)

### routes/admin.py

`POST /api/reload` → re-download all snapshots from GCS (hot reload, no restart)
`POST /ingest/trigger` → launch athanor-ingest Cloud Run Job via Cloud Run Jobs API

### docker/athanor-rag/Dockerfile

```dockerfile
FROM python:3.12-slim

RUN useradd -m -u 1001 rag
USER 1001
WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY --chown=rag:rag . .
COPY --chown=rag:rag ../../lib ./lib

EXPOSE 8080
HEALTHCHECK --interval=30s --timeout=10s --start-period=30s CMD curl -f http://localhost:8080/health || exit 1

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8080"]
```

### docker/athanor-rag/requirements.txt

```
fastapi>=0.110
uvicorn[standard]>=0.29
chromadb>=0.5
openai>=1.0
httpx>=0.27
google-cloud-storage>=2.14
google-cloud-secret-manager>=2.20
networkx>=3.2
pyyaml>=6.0
```

---

## Step 11: Terraform

### infra/kms-rag.tf

```hcl
resource "google_kms_key_ring" "rag" {
  name     = "athanor-rag-keyring"
  location = "europe-west9"
  labels   = var.labels
}

resource "google_kms_crypto_key" "rag_data" {
  name            = "athanor-rag-data-key"
  key_ring        = google_kms_key_ring.rag.id
  rotation_period = "7776000s"  # 90 days
  labels          = var.labels
}

# Grant GCS service account access to use the key
resource "google_kms_crypto_key_iam_member" "gcs_kms" {
  crypto_key_id = google_kms_crypto_key.rag_data.id
  role          = "roles/cloudkms.cryptoKeyEncrypterDecrypter"
  member        = "serviceAccount:service-${data.google_project.current.number}@gs-project-accounts.iam.gserviceaccount.com"
}
```

### infra/gcs-rag.tf

```hcl
resource "google_storage_bucket" "rag_data" {
  name          = "athanor-ai-rag-data"
  location      = "europe-west9"
  storage_class = "STANDARD"
  labels        = var.labels

  versioning { enabled = false }  # Snapshots are overwritten in-place; backup bucket handles recovery

  default_encryption {
    default_kms_key_name = google_kms_crypto_key.rag_data.id
  }

  lifecycle_rule {
    condition { age = 1 }  # Clean up incomplete multipart uploads
    action { type = "AbortIncompleteMultipartUpload" }
  }
}

resource "google_storage_bucket" "rag_backup" {
  name          = "athanor-ai-rag-backup"
  location      = "europe-west9"
  storage_class = "NEARLINE"
  labels        = var.labels

  versioning { enabled = false }

  default_encryption {
    default_kms_key_name = google_kms_crypto_key.rag_data.id
  }

  lifecycle_rule {
    condition { age = 90 }
    action { type = "Delete" }
  }
}
```

### infra/secrets-rag.tf

```hcl
resource "google_secret_manager_secret" "rclone_conf" {
  secret_id = "athanor-rclone-conf"
  labels    = var.labels
  replication { auto {} }
}

resource "google_secret_manager_secret" "rag_api_key" {
  secret_id = "athanor-rag-api-key"
  labels    = var.labels
  replication { auto {} }
}
```

### infra/iam-rag.tf

```hcl
resource "google_service_account" "rag_sa" {
  account_id   = "athanor-rag-sa"
  display_name = "Athanor RAG Service Account"
}

resource "google_storage_bucket_iam_member" "rag_data_admin" {
  bucket = google_storage_bucket.rag_data.name
  role   = "roles/storage.objectAdmin"
  member = "serviceAccount:${google_service_account.rag_sa.email}"
}

resource "google_storage_bucket_iam_member" "rag_backup_admin" {
  bucket = google_storage_bucket.rag_backup.name
  role   = "roles/storage.objectAdmin"
  member = "serviceAccount:${google_service_account.rag_sa.email}"
}

resource "google_project_iam_member" "rag_run_developer" {
  project = var.project_id
  role    = "roles/run.developer"
  member  = "serviceAccount:${google_service_account.rag_sa.email}"
}

resource "google_secret_manager_secret_iam_member" "rag_rclone_access" {
  secret_id = google_secret_manager_secret.rclone_conf.secret_id
  role      = "roles/secretmanager.secretAccessor"
  member    = "serviceAccount:${google_service_account.rag_sa.email}"
}

resource "google_secret_manager_secret_iam_member" "rag_api_key_access" {
  secret_id = google_secret_manager_secret.rag_api_key.secret_id
  role      = "roles/secretmanager.secretAccessor"
  member    = "serviceAccount:${google_service_account.rag_sa.email}"
}

# Also grant access to the VertexAI proxy key
resource "google_secret_manager_secret_iam_member" "rag_vertexai_key_access" {
  secret_id = google_secret_manager_secret.vertexai_proxy_key.secret_id
  role      = "roles/secretmanager.secretAccessor"
  member    = "serviceAccount:${google_service_account.rag_sa.email}"
}
```

### infra/cloud-run-rag.tf

```hcl
resource "google_cloud_run_v2_service" "athanor_rag" {
  name     = "athanor-rag"
  location = var.region
  labels   = var.labels

  template {
    service_account = google_service_account.rag_sa.email

    scaling {
      min_instance_count = 0
      max_instance_count = 1
    }

    containers {
      image = "${var.region}-docker.pkg.dev/${var.project_id}/athanor-images/athanor-rag:latest"

      resources {
        limits = { memory = "2Gi", cpu = "1" }
        startup_cpu_boost = true
      }

      env { name = "RAG_GCS_BUCKET",   value = google_storage_bucket.rag_data.name }
      env { name = "VERTEXAI_PROXY_URL", value = google_cloud_run_v2_service.vertexai_proxy.uri }
      env { name = "INGEST_JOB_NAME",  value = "projects/${var.project_id}/locations/${var.region}/jobs/athanor-ingest" }
      env { name = "GCP_PROJECT_ID",   value = var.project_id }
      env { name = "GCP_REGION",       value = var.region }
      env {
        name = "VERTEXAI_PROXY_KEY"
        value_source { secret_key_ref { secret = google_secret_manager_secret.vertexai_proxy_key.secret_id; version = "latest" } }
      }
      env {
        name = "RAG_API_KEY"
        value_source { secret_key_ref { secret = google_secret_manager_secret.rag_api_key.secret_id; version = "latest" } }
      }

      startup_probe {
        http_get { path = "/health" }
        initial_delay_seconds = 15
        period_seconds        = 10
        failure_threshold     = 18  # 3 minutes total
      }
    }
  }
}

resource "google_cloud_run_v2_service_iam_member" "rag_public" {
  name     = google_cloud_run_v2_service.athanor_rag.name
  location = var.region
  role     = "roles/run.invoker"
  member   = "allUsers"  # Auth handled by RAG_API_KEY Bearer token
}

resource "google_cloud_run_v2_job" "athanor_ingest" {
  name     = "athanor-ingest"
  location = var.region
  labels   = var.labels

  template {
    template {
      service_account = google_service_account.rag_sa.email
      max_retries     = 1

      containers {
        image = "${var.region}-docker.pkg.dev/${var.project_id}/athanor-images/athanor-ingest:latest"

        resources { limits = { memory = "2Gi", cpu = "1" } }

        env { name = "CONNECTOR_TYPE",      value = var.connector_type }
        env { name = "PROTON_DRIVE_ROOT",   value = var.proton_drive_root }
        env { name = "RAG_GCS_BUCKET",      value = google_storage_bucket.rag_data.name }
        env { name = "RAG_GCS_BACKUP_BUCKET", value = google_storage_bucket.rag_backup.name }
        env { name = "VERTEXAI_PROXY_URL",  value = google_cloud_run_v2_service.vertexai_proxy.uri }
        env { name = "OCR_MODEL",           value = var.ocr_model }
        env { name = "EMBED_MODEL",         value = var.embed_model }
        env { name = "GCP_PROJECT_ID",      value = var.project_id }
        env { name = "GCP_REGION",          value = var.region }
        env {
          name = "RCLONE_CONFIG_SECRET"
          value = google_secret_manager_secret.rclone_conf.secret_id
        }
        env {
          name = "VERTEXAI_PROXY_KEY"
          value_source { secret_key_ref { secret = google_secret_manager_secret.vertexai_proxy_key.secret_id; version = "latest" } }
        }
      }
    }
  }
}

# Cloud Scheduler — europe-west1 (scheduler not available in europe-west9)
resource "google_cloud_scheduler_job" "athanor_ingest_trigger" {
  name      = "athanor-ingest-daily"
  region    = "europe-west1"
  schedule  = "0 3 * * *"
  time_zone = "Europe/Paris"

  http_target {
    http_method = "POST"
    uri         = "https://${var.region}-run.googleapis.com/apis/run.googleapis.com/v1/namespaces/${var.project_id}/jobs/athanor-ingest:run"

    oauth_token {
      service_account_email = google_service_account.rag_sa.email
    }
  }
}
```

### infra/variables.tf — additions

```hcl
variable "connector_type" {
  type        = string
  description = "Drive connector type (only 'proton' implemented)"
  default     = "proton"
}

variable "proton_drive_root" {
  type        = string
  description = "Root path on Proton Drive to scan for athanor.* markers"
  default     = "/"
}

variable "ocr_model" {
  type        = string
  description = "Gemini model for OCR (configurable for future model upgrades)"
  default     = "gemini-2.5-flash"
}

variable "embed_model" {
  type        = string
  description = "VertexAI embedding model"
  default     = "text-multilingual-embedding-002"
}

variable "rag_api_key" {
  type        = string
  sensitive   = true
  description = "Bearer token for athanor-rag inbound API auth"
}

variable "rclone_conf" {
  type        = string
  sensitive   = true
  description = "Full content of rclone.conf for Proton Drive"
}
```

---

## Step 13: pipelines/pipes/athanor_project.py

OpenWebUI Pipe function. Routes requests to athanor-rag based on `model` field.

```python
"""
OpenWebUI Pipe: routes to athanor-rag /v1/chat/completions.
Installed once in OpenWebUI. Model name in the request = project name.
The pipe dynamically lists available projects from /api/projects and
registers them as models in OpenWebUI.
"""

from pydantic import BaseModel
import httpx


class Pipe:
    class Valves(BaseModel):
        RAG_URL: str = ""         # athanor-rag service URL
        RAG_API_KEY: str = ""     # Bearer token

    def __init__(self):
        self.valves = self.Valves()

    def pipes(self) -> list[dict]:
        """Called by OpenWebUI to list available models."""
        try:
            resp = httpx.get(
                f"{self.valves.RAG_URL}/api/projects",
                headers={"Authorization": f"Bearer {self.valves.RAG_API_KEY}"},
                timeout=10,
            )
            projects = resp.json()
            return [{"id": name, "name": name.capitalize()} for name in projects]
        except Exception:
            return []

    async def pipe(self, body: dict) -> str | dict:
        """Forward request to athanor-rag /v1/chat/completions."""
        async with httpx.AsyncClient() as client:
            resp = await client.post(
                f"{self.valves.RAG_URL}/v1/chat/completions",
                json=body,
                headers={"Authorization": f"Bearer {self.valves.RAG_API_KEY}"},
                timeout=60,
            )
            return resp.json()
```

---

## Step 14: Checkpoint bidirectional

### In ingest_job.py (already in step 9, step 14):
- `connector.read_checkpoint(project.name)` → reads from Proton Drive
- Write to GCS `checkpoints/{project.name}.md`
- After conversation in RAG service: `POST /api/projects/{name}/checkpoint` with new content
- RAG service writes to GCS, then (FUTURE extension): calls back to connector to push to Proton Drive

### In docker/athanor-rag/routes/checkpoint.py:
```
POST /api/projects/{name}/checkpoint
  body: {"content": str}
  → writes to GCS checkpoints/{name}.md
  → optionally pushes to Proton Drive (requires rclone in the RAG container — future work)
```

For MVP: checkpoint is GCS-only (readable by RAG, written by ingest and by RAG). Proton Drive write-back is added in a follow-up.

---

## Environment Variables Reference

### athanor-ingest

| Variable | Source | Example |
|---|---|---|
| `CONNECTOR_TYPE` | Terraform env | `proton` |
| `PROTON_DRIVE_ROOT` | Terraform env | `/` |
| `RCLONE_CONFIG_SECRET` | Terraform env | `athanor-rclone-conf` |
| `RAG_GCS_BUCKET` | Terraform env | `athanor-ai-rag-data` |
| `RAG_GCS_BACKUP_BUCKET` | Terraform env | `athanor-ai-rag-backup` |
| `VERTEXAI_PROXY_URL` | Terraform env | `https://athanor-vertexai-proxy-xxx.run.app` |
| `VERTEXAI_PROXY_KEY` | Secret Manager | (sensitive) |
| `OCR_MODEL` | Terraform env | `gemini-2.5-flash` |
| `EMBED_MODEL` | Terraform env | `text-multilingual-embedding-002` |
| `GCP_PROJECT_ID` | Terraform env | `athanor-ai` |
| `GCP_REGION` | Terraform env | `europe-west9` |

### athanor-rag

| Variable | Source | Example |
|---|---|---|
| `RAG_GCS_BUCKET` | Terraform env | `athanor-ai-rag-data` |
| `VERTEXAI_PROXY_URL` | Terraform env | `https://...` |
| `VERTEXAI_PROXY_KEY` | Secret Manager | (sensitive) |
| `RAG_API_KEY` | Secret Manager | (sensitive) |
| `INGEST_JOB_NAME` | Terraform env | `projects/athanor-ai/locations/europe-west9/jobs/athanor-ingest` |
| `GCP_PROJECT_ID` | Terraform env | `athanor-ai` |
| `GCP_REGION` | Terraform env | `europe-west9` |

---

## End-to-End Verification Checklist

```bash
# 1. Place marker in Proton Drive
#    Create file "athanor.test" (empty) in a Proton Drive folder with 1 PDF

# 2. Run ingest job
gcloud run jobs execute athanor-ingest --region europe-west9

# 3. CRITICAL: verify no PDF on GCS
gcloud storage ls "gs://athanor-ai-rag-data/**/*.pdf"  # must return nothing
gcloud storage ls "gs://athanor-ai-rag-data/.vectordb/"  # must show test.json.gz

# 4. Check backup
gcloud storage ls "gs://athanor-ai-rag-backup/$(date +%Y-%m-%d)/.vectordb/"

# 5. List projects
curl -H "Authorization: Bearer $RAG_API_KEY" https://athanor-rag-.../api/projects

# 6. Search
curl -X POST -H "Authorization: Bearer $RAG_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"query": "test query", "top_k": 3}' \
  https://athanor-rag-.../api/projects/test/search

# 7. Chat (OpenAI-compatible)
curl -X POST -H "Authorization: Bearer $RAG_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"model": "test", "messages": [{"role": "user", "content": "What is in this document?"}]}' \
  https://athanor-rag-.../v1/chat/completions

# 8. Verify no OpenRouter calls
# Check VertexAI proxy logs — should show embedding + chat calls, NO OpenRouter calls

# 9. Scale-to-zero test
# Wait 15 minutes idle, then verify 0 instances, then query again (cold start < 3 min)

# 10. Isolation test (feeds_into)
# Create athanor.finances (with feeds_into: [immobilier]) and athanor.immobilier
# Ingest → search "immobilier" project → should find finances documents
# Search "finances" project → should NOT find immobilier documents
```
