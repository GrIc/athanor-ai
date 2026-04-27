---
name: docker
description: >
  Docker and container patterns for Athanor. Use when building images,
  writing Dockerfiles, configuring Artifact Registry, or working on
  OpenWebUI custom images with pipelines.
tools: Read, Edit, Write, Bash, Glob, Grep
---

# Docker Skill — Athanor Project

## Container Registry

- **Registry**: `europe-west9-docker.pkg.dev/athanor-ai/athanor-images`
- **Auth**: `gcloud auth configure-docker europe-west9-docker.pkg.dev`
- **Build**: Cloud Build (via `gcloud builds submit`), not local Docker

## Images

| Image | Source | Built by |
|-------|--------|----------|
| `openwebui:latest` | `docker/openwebui/Dockerfile` | Cloud Build (terraform_data trigger) |
| `vertexai-proxy:latest` | `docker/vertexai-proxy/Dockerfile` | Cloud Build (terraform_data trigger) |

Both images are rebuilt automatically when their source files change (via `filemd5()` triggers in `infra/artifact-registry.tf`).

## Dockerfile Standards

- Multi-stage builds to minimize image size
- Non-root user (`USER 1001`)
- Pinned base image tags (no `:latest` in production Dockerfiles)
- `HEALTHCHECK` instruction
- Labels: `org.opencontainers.image.source`, `org.opencontainers.image.version`

## Build & Push (manual, if needed)

```bash
# Build via Cloud Build (preferred — same as CI/CD)
gcloud builds submit docker/vertexai-proxy \
  --tag europe-west9-docker.pkg.dev/athanor-ai/athanor-images/vertexai-proxy:latest \
  --project athanor-ai

# Then update Cloud Run to use the new image
gcloud run services update athanor-vertexai-proxy \
  --region europe-west9 \
  --image europe-west9-docker.pkg.dev/athanor-ai/athanor-images/vertexai-proxy:latest
```
