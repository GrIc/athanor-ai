# Athanor — Deployment & CI/CD

## Manual Deployment (Phase 1)

```bash
# 1. Authenticate
gcloud auth login
gcloud config set project athanor-ai

# 2. Initialize Terraform
cd infra
terraform init

# 3. Plan and review
terraform plan -var-file=envs/prod.tfvars

# 4. Apply
terraform apply -var-file=envs/prod.tfvars

# 5. Verify
gcloud run services describe athanor-openwebui --region europe-west9
curl -s https://athanor-openwebui-HASH-ew.a.run.app/health
```

## CI/CD Pipeline (Phase 2)

GitHub Actions workflow (`.github/workflows/deploy.yml`):

1. **On push to `main`**:
   - `terraform fmt -check`
   - `terraform validate`
   - `terraform plan` (comment on PR)
2. **On merge to `main`**:
   - `terraform apply -auto-approve`
   - Smoke test (curl health endpoint)
3. **On push to `docker/**`**:
   - Build custom image
   - Push to Artifact Registry
   - Update Cloud Run revision

## Rollback

```bash
# List revisions
gcloud run revisions list --service athanor-openwebui --region europe-west9

# Route 100% traffic to previous revision
gcloud run services update-traffic athanor-openwebui \
  --region europe-west9 \
  --to-revisions=athanor-openwebui-PREVIOUS=100
```

## Environment Promotion

```
dev (local/terraform plan) → prod (europe-west9)
```

Single environment for now (personal project). Add `dev` Cloud Run service if needed later.