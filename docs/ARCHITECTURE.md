# Athanor — Architecture

## System Overview

```
┌─────────────────────────────────────────────────────────────┐
│                         CLIENTS                             │
│  Web/Mobile (PWA)  ──┐                                      │
│  VSCode/Roo Code   ──┤                                      │
│  Terminal CLI      ──┤                                      │
│  Home Assistant    ──┘                                      │
└─────────────────────────────────────────────────────────────┘
              │
              ▼
┌──────────────────────────────────────────────────────────────────────┐
│  GCP Cloud Run (europe-west9)                                        │
│                                                                      │
│  ┌─────────────────────────────┐     ┌──────────────────────────┐   │
│  │  athanor-openwebui          │     │  OpenRouter.ai (SaaS)    │   │
│  │  + Pipe functions           │────►│  General LLMs            │   │
│  │  + Budget/parental filters  │     │  (Claude, GPT, Mistral)  │   │
│  │  + SQLite / GCS FUSE        │     └──────────────────────────┘   │
│  └────────────┬────────────────┘                                     │
│               │ Pipe calls (HTTP + Bearer)                           │
│               ▼                                                      │
│  ┌─────────────────────────────┐     ┌──────────────────────────┐   │
│  │  athanor-rag  [Phase 3]     │────►│  athanor-vertexai-proxy  │   │
│  │  FastAPI                    │     │  Gemini models (EU only) │   │
│  │  - /v1/chat/completions     │     │  + embeddings            │   │
│  │  - /api/search              │     └──────────────────────────┘   │
│  │  - /ingest/trigger          │           │ VertexAI API           │
│  │  ChromaDB (in-memory)       │           ▼                        │
│  │  loaded from GCS snapshot   │     ┌──────────────────────────┐   │
│  └─────────────────────────────┘     │  GCP Vertex AI           │   │
│                                      │  (europe-west9)          │   │
│  ┌─────────────────────────────┐     └──────────────────────────┘   │
│  │  athanor-ingest  [Phase 3]  │                                     │
│  │  Cloud Run Job (scheduled)  │                                     │
│  │  Parse PDF/DOCX/PPTX        │                                     │
│  │  Embed via VertexAI Proxy   │                                     │
│  │  Dump ChromaDB → GCS        │                                     │
│  └─────────────────────────────┘                                     │
│                                                                      │
│  ┌─────────────────────────────┐     ┌──────────────────────────┐   │
│  │  athanor-cost-dashboard     │     │  GCS Buckets             │   │
│  │  athanor-weekly-digest      │     │  - athanor-data/         │   │
│  │  (existing)                 │     │    (OpenWebUI SQLite)    │   │
│  └─────────────────────────────┘     │  - athanor-rag-data/     │   │
│                                      │    documents/            │   │
│                                      │    .vectordb/ (snapshots)│   │
│                                      └──────────────────────────┘   │
└──────────────────────────────────────────────────────────────────────┘
```

### Data Sovereignty Rule

**RAG pipeline (family documents) → VertexAI only. Never OpenRouter.**

This is enforced architecturally: `athanor-rag` only has `VERTEXAI_PROXY_URL` in its config. There is no OpenRouter API key in the RAG service.

## Design Principles

1. **OPEX-only**: zero fixed costs — Cloud Run scale-to-zero + pay-per-token LLM
2. **Modular**: each component is a replaceable container
3. **EU sovereign**: all data in europe-west9, Proton Drive as family data source
4. **Observable**: cost, performance, and carbon tracked from day 1

## Data Flows

### Standard LLM (general use)
1. User opens OpenWebUI → selects a model (Claude, Gemini, etc.)
2. OpenWebUI sends request to OpenRouter API
3. OpenRouter routes to the selected LLM provider
4. Response flows back through OpenWebUI to the user
5. Conversations stored in SQLite on GCS FUSE

### RAG / Family Documents (sovereign)
1. User selects "Document Search" (or other RAG agent) in OpenWebUI
2. OpenWebUI Pipe function calls `athanor-rag /v1/chat/completions`
3. `athanor-rag` searches in-memory ChromaDB (loaded from GCS snapshots at startup)
4. `athanor-rag` calls `athanor-vertexai-proxy` for embeddings + LLM response
5. VertexAI Proxy calls GCP Vertex AI (eu-west9 only)
6. Response flows back to OpenWebUI → user

### Document Ingestion (nightly or on-demand)
1. Documents synced from Proton Drive → GCS via rclone
2. `athanor-ingest` job runs: parse → chunk → embed → ChromaDB dump → GCS
3. `athanor-rag` calls `POST /api/reload` or restarts to load new snapshot

## Cost Model (Monthly Estimates)

| Component | Idle | Light | Moderate | Heavy |
|-----------|------|-------|----------|-------|
| Cloud Run | €0 | €2 | €10 | €25 |
| GCS | €0 | <€1 | <€1 | €2 |
| OpenRouter tokens | €0 | €5 | €30 | €100 |
| **Total** | **€0** | **~€8** | **~€40** | **~€130** |

## Security Boundaries

- GCP IAM: least-privilege service accounts per component
- Secrets: all API keys in Secret Manager, mounted as env vars
- Network: Cloud Run is public (authenticated via OpenWebUI RBAC)
- Data: family data in Proton Drive (E2E encrypted), synced via rclone to GCS for RAG
- Parental: model whitelisting + chat history retention + toxic message filter