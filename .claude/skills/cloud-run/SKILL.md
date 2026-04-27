---
name: cloud-run
description: >
  GCP Cloud Run deployment patterns for Athanor. Use when deploying
  containers, configuring OpenWebUI on Cloud Run, setting up env vars,
  managing revisions, or troubleshooting cold starts and scaling.
tools: Read, Edit, Write, Bash, Glob, Grep
---

# Cloud Run Skill — Athanor Project

## Services

### OpenWebUI
- **Image**: `ghcr.io/open-webui/open-webui:main` (or custom from Artifact Registry)
- **Service name**: `athanor-openwebui`
- **Port**: 8080
- **Access**: public (`allUsers` → `roles/run.invoker`)

### VertexAI Proxy
- **Image**: `europe-west9-docker.pkg.dev/athanor-ai/athanor-images/vertexai-proxy:latest`
- **Service name**: `athanor-vertexai-proxy`
- **Port**: 8080
- **Access**: public (app-level auth via `PROXY_API_KEY`)
- **Source**: `docker/vertexai-proxy/` (FastAPI + httpx + google-auth)

Both services: **region europe-west9**, **min instances 0** (scale-to-zero).

### Required Environment Variables

**OpenWebUI:**
```
OPENAI_API_BASE_URL=https://openrouter.ai/api/v1
OPENAI_API_KEY=<from Secret Manager>
WEBUI_SECRET_KEY=<from Secret Manager>
WEBUI_AUTH=true
```

**VertexAI Proxy:**
```
VERTEXAI_PROJECT_ID=athanor-ai
VERTEXAI_LOCATION=europe-west9
PROXY_API_KEY=<from Secret Manager>
```

## GCS FUSE for SQLite (current MVP)

```hcl
volume:
  name: gcs-fuse
  gcs:
    bucket: athanor-ai-athanor-data
    readOnly: false
volumeMount:
  name: gcs-fuse
  mountPath: /app/backend/data
```

SQLite + GCS FUSE has concurrency limits. Fine for family use. Migrate to Cloud SQL PostgreSQL when needed.

## Useful Commands

```bash
# Check logs
gcloud run services logs read athanor-openwebui --region europe-west9 --limit 50
gcloud run services logs read athanor-vertexai-proxy --region europe-west9 --limit 50

# Check current revision
gcloud run revisions list --service athanor-openwebui --region europe-west9
gcloud run revisions list --service athanor-vertexai-proxy --region europe-west9

# Force redeploy (same image, new revision)
gcloud run services update athanor-openwebui --region europe-west9 \
  --image <current-image>
```
