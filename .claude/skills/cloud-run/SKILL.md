---
name: cloud-run
description: >
  GCP Cloud Run deployment patterns for Athanor. Use when deploying
  containers, configuring OpenWebUI on Cloud Run, setting up env vars,
  managing revisions, or troubleshooting cold starts and scaling.
tools: Read, Edit, Write, Bash, Glob, Grep
---

# Cloud Run Skill — Athanor Project

## OpenWebUI Deployment

**Image**: `ghcr.io/open-webui/open-webui:main` (or pinned tag)
**Region**: `europe-west9` (Paris)
**Port**: 8080 (OpenWebUI default)

### Required Environment Variables

```
OPENAI_API_BASE_URL=https://openrouter.ai/api/v1
OPENAI_API_KEY=<from Secret Manager>
WEBUI_SECRET_KEY=<from Secret Manager>
WEBUI_AUTH=true
DATABASE_URL=<Cloud SQL connection string or omit for SQLite>
```

### Scale-to-Zero Config

```yaml
# Cloud Run service spec essentials
scaling:
  minInstanceCount: 0 # MANDATORY — zero cost at rest
  maxInstanceCount: 2 # Cost cap
resources:
  limits:
    cpu: "1"
    memory: "1Gi" # OpenWebUI needs ~512Mi minimum
startupProbe:
  httpGet:
    path: /health
    port: 8080
  initialDelaySeconds: 10
  periodSeconds: 5
```

### Cold Start Optimization

- OpenWebUI cold start: ~15-30s depending on memory
- Set `cpu-boost` on Cloud Run for faster startup
- Consider `min-instances: 1` ONLY if family uses it daily (adds ~€15/mo)

## GCS FUSE for SQLite (MVP)

```
# Mount GCS bucket as filesystem for SQLite persistence
# Add to Cloud Run: --execution-environment gen2 --add-volume=...
volume:
  name: gcs-fuse
  gcs:
    bucket: athanor-openwebui-data
    readOnly: false
volumeMount:
  name: gcs-fuse
  mountPath: /app/backend/data
```

⚠️ SQLite + GCS FUSE has concurrency limits. Fine for MVP (1 family), migrate to Cloud SQL for multi-user production.

## Useful Commands

```bash
# Deploy new revision
gcloud run deploy athanor-openwebui \
  --image ghcr.io/open-webui/open-webui:main \
  --region europe-west9 \
  --allow-unauthenticated \
  --set-secrets "OPENAI_API_KEY=openrouter-key:latest,WEBUI_SECRET_KEY=webui-secret:latest"

# Check logs
gcloud run services logs read athanor-openwebui --region europe-west9 --limit 50

# Check current revision
gcloud run revisions list --service athanor-openwebui --region europe-west9
```
