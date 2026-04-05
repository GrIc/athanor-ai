# Terraform Mode Rules — Athanor

## Conventions
- Provider: `google`, pinned version in `infra/providers.tf`
- Backend: GCS bucket for remote state (`athanor-ai-tfstate`)
- Region: `europe-west9` (Paris) — hardcoded default
- Naming: `athanor-{component}` (e.g., `athanor-openwebui`, `athanor-vertexai-proxy`)

## File Structure (flat, no modules yet)
```
infra/
├── providers.tf          # Provider + GCS backend config
├── apis.tf               # GCP API enablement
├── variables.tf          # Root variables
├── outputs.tf            # Root outputs
├── cloud-run.tf          # OpenWebUI + VertexAI Proxy services
├── gcs.tf                # GCS buckets
├── iam.tf                # Service account permissions
├── iam-cicd.tf           # WIF pool + CI service account
├── artifact-registry.tf  # Container registry + Cloud Build triggers
├── budget.tf             # Budget alerts
└── envs/
    ├── prod.tfvars
    └── .env.prod.example  # Secret vars template (local only)
```

## Labels — MANDATORY on every resource
```hcl
labels = var.labels
# Default: { project = "athanor", env = "prod", managed-by = "terraform" }
```

## Patterns
- Cloud Run: always `min_instance_count = 0`
- Secrets: always via `google_secret_manager_secret_version`, never inline
- Images built via `terraform_data` with `filemd5()` triggers + `gcloud builds submit`

## Validation Before Apply
1. `terraform fmt -check -recursive`
2. `terraform validate`
3. `terraform plan -var-file=envs/prod.tfvars`
4. Verify: no resources outside EU, all labels present, no plaintext secrets
