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

## Dockerfile Standards

- Multi-stage builds to minimize image size
- Non-root user (`USER 1001`)
- Pinned base image tags (no `:latest` in production)
- `HEALTHCHECK` instruction where applicable
- Labels: `org.opencontainers.image.source`, `org.opencontainers.image.version`

## Custom OpenWebUI Image (when needed)

```dockerfile
FROM docker.io/open-webui/open-webui:main AS base

# Add custom pipelines
COPY pipelines/ /app/backend/pipelines/

# Add custom tools
COPY tools/ /app/backend/tools/

# No need to change CMD — OpenWebUI handles it
```

## Build & Push

```bash
# Build locally
docker build -t athanor-openwebui:local -f docker/openwebui/Dockerfile .

# Tag for Artifact Registry
docker tag athanor-openwebui:local \
  europe-west9-docker.pkg.dev/athanor-ai/athanor-images/openwebui:$(git rev-parse --short HEAD)

# Push
docker push europe-west9-docker.pkg.dev/athanor-ai/athanor-images/openwebui:$(git rev-parse --short HEAD)
```
