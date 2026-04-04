# Athanor — Quick Reference

## Essential Commands
```bash
terraform -chdir=infra init                          # Initialize TF
terraform -chdir=infra plan -var-file=envs/prod.tfvars  # Preview changes
terraform -chdir=infra apply -var-file=envs/prod.tfvars  # Apply changes
gcloud run services list --region europe-west9       # List Cloud Run services
gcloud run services logs read athanor-openwebui --region europe-west9 --limit 20
docker build -t athanor-openwebui:local -f docker/openwebui/Dockerfile .
```

## GCP Project
- **Project ID**: `athanor-ai`
- **Region**: `europe-west9` (Paris)
- **Billing**: Budget alerts at 50/80/100%

## Key URLs
- OpenRouter API: `https://openrouter.ai/api/v1`
- OpenWebUI image: `ghcr.io/open-webui/open-webui:main`
- Artifact Registry: `europe-west9-docker.pkg.dev/athanor-ai/athanor-images`

## Secret Manager Keys
- `openrouter-key` — OpenRouter API key
- `webui-secret` — OpenWebUI session secret
- `db-password` — PostgreSQL password (when migrated from SQLite)