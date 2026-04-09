# Athanor — Global Rules (All Modes)

## Project Identity
Athanor: self-hosted family AI platform — OpenWebUI + OpenRouter + VertexAI Proxy on GCP Cloud Run (europe-west9).
Repo: `athanor-ai` | License: Apache 2.0 | All code, docs, commits: **English only**.

## Critical Rules — NEVER Violate
1. **No hardcoded secrets** — GCP Secret Manager or env vars only
2. **All GCP resources in Terraform** — `infra/` directory, no console clicks
3. **Scale-to-zero mandatory** — reject any component that costs money at rest
4. **EU regions only** — `europe-west9` (Paris) or `europe-west1` (Belgium)
5. **Conventional commits** — `feat:`, `fix:`, `infra:`, `docs:`, `chore:`
6. **No documents on GCS** — Proton Drive files are downloaded to `/tmp/ingest/{project}/` and deleted in a `finally` block. The GCS bucket `athanor-ai-rag-data` contains ONLY: `.vectordb/*.json.gz`, `.graphdb/*/`, `checkpoints/*.md`, `manifest.json`. Never PDF, DOCX, images.
7. **ChromaDB EphemeralClient only** — never `PersistentClient` or SQLite-on-GCS-FUSE. Load from `json.gz` snapshot at startup, save back to GCS after ingest.
8. **VertexAI Proxy only for RAG** — all LLM/embedding calls in `athanor-rag` and `athanor-ingest` go through `VERTEXAI_PROXY_URL`. Never OpenRouter.

## Project Structure
```
athanor-ai/
├── infra/              # Terraform (flat structure, envs/ for tfvars)
├── docker/             # Custom Dockerfiles (openwebui, vertexai-proxy, athanor-rag, athanor-ingest)
├── lib/                # Shared Python libraries (Phase 3 RAG)
│   ├── connectors/     # DriveConnector ABC + ProtonDriveConnector (rclone)
│   ├── rag_core/       # VectorStore, ingest parsers, OCR, graph, client
│   └── agents/         # BaseAgent, render_system_prompt()
├── agents/
│   └── defs/           # Agent template markdown (default.md — one generic template)
├── pipelines/          # OpenWebUI pipelines (Python)
├── scripts/            # Utility scripts (setup, deploy)
├── docs/               # Extended docs (see docs/INDEX.md)
├── .roo/               # Roo Code rules and modes
└── .claude/            # Claude Code config, skills, hooks, agents
```

## Tech Stack
- IaC: Terraform + GCS backend (`athanor-ai-tfstate`)
- Runtime: Cloud Run (europe-west9), scale-to-zero
- LLM: OpenRouter (200+ models) + VertexAI Proxy (Gemini, EU sovereign)
- Frontend: OpenWebUI (`ghcr.io/open-webui/open-webui:main`)
- Secrets: GCP Secret Manager
- CI/CD: GitHub Actions + Workload Identity Federation (no long-lived keys)
- Container registry: Artifact Registry (`athanor-images`)

## Response Style
- Be concise — no fluff, no preamble
- Produce complete, working code — not partial snippets
- Include exact shell commands to deploy/test
- When modifying files, use diff-based edits (Roo's strength)
