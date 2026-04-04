# Athanor — Architecture

## System Overview

```
┌────────────────────────────────────────────────────────┐
│                     CLIENTS                            │
│  Web/Mobile (PWA) ──┐                                  │
│  VSCode/Roo Code ───┤── OpenRouter ──► LLM Providers   │
│  Terminal CLI ──────┤   (routing)     (Claude, GPT,    │
│  Home Assistant ────┘                  Mistral, etc.)  │
└────────────────────────────────────────────────────────┘
              │
              ▼
┌────────────────────────┐     ┌─────────────────────┐
│  GCP Cloud Run         │     │  OpenRouter.ai      │
│  (europe-west9)        │     │  (SaaS, pay/token)  │
│                        │     │                     │
│  ┌──────────────────┐  │     │  Single API URL     │
│  │ OpenWebUI        │──┼────►│  Model switching    │
│  │ + Pipelines      │  │     │  Analytics          │
│  │ + RAG (ChromaDB) │  │     └─────────────────────┘
│  └──────────────────┘  │
│                        │
│  ┌──────────────────┐  │     ┌─────────────────────┐
│  │ SQLite + GCS FUSE│  │     │  Observability      │
│  │ (MVP)            │  │     │  - GCP Billing API  │
│  └──────────────────┘  │     │  - Carbon Footprint │
│                        │     │  - Langfuse (opt.)  │
│  ┌──────────────────┐  │     └─────────────────────┘
│  │ GCS Buckets      │  │
│  │ (storage/RAG)    │  │     ┌─────────────────────┐
│  └──────────────────┘  │     │  Home Assistant     │
└────────────────────────┘     │  (Raspberry Pi)     │
                               │  Local network only │
                               └─────────────────────┘
```

## Design Principles

1. **OPEX-only**: zero fixed costs — Cloud Run scale-to-zero + pay-per-token LLM
2. **Modular**: each component is a replaceable container
3. **EU sovereign**: all data in europe-west9, Proton Drive as family data source
4. **Observable**: cost, performance, and carbon tracked from day 1

## Data Flow

1. User opens OpenWebUI (web/PWA) or sends request via IDE/CLI
2. OpenWebUI formats the request and sends to OpenRouter API
3. OpenRouter routes to the selected LLM provider
4. Response flows back through OpenWebUI to the user
5. Conversations stored in SQLite/PostgreSQL on Cloud Run
6. RAG documents stored in GCS, embeddings in ChromaDB (co-located)

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