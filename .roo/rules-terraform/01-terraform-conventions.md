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
├── variables.tf          # Root variables (add rag_api_key, rclone_conf, ocr_model, embed_model)
├── outputs.tf            # Root outputs
├── cloud-run.tf          # OpenWebUI + VertexAI Proxy services
├── gcs.tf                # GCS buckets (existing: openwebui data)
├── iam.tf                # Service account permissions (existing)
├── iam-cicd.tf           # WIF pool + CI service account
├── artifact-registry.tf  # Container registry + Cloud Build triggers
├── budget.tf             # Budget alerts
│
│   ── Phase 3 RAG (new files) ──
├── kms-rag.tf            # Cloud KMS keyring + crypto key (europe-west9, 90-day rotation)
├── gcs-rag.tf            # athanor-ai-rag-data (Standard) + athanor-ai-rag-backup (Nearline), both CMEK
├── secrets-rag.tf        # athanor-rclone-conf + athanor-rag-api-key in Secret Manager
├── iam-rag.tf            # athanor-rag-sa: objectAdmin on both buckets, run.developer, secretAccessor
└── cloud-run-rag.tf      # athanor-rag service + athanor-ingest job + Cloud Scheduler trigger
│
└── envs/
    ├── prod.tfvars
    └── .env.prod.example  # Secret vars template (local only)
```

## Phase 3 Terraform Notes
- Cloud Scheduler MUST be in `europe-west1` — scheduler not available in `europe-west9`
- CMEK: KMS key binding requires `google_kms_crypto_key_iam_member` for GCS service account (`serviceAccount:service-{project_number}@gs-project-accounts.iam.gserviceaccount.com`)
- athanor-rag service: `allUsers` invoker (auth enforced by `RAG_API_KEY` Bearer token, same pattern as vertexai-proxy)
- athanor-ingest job: `max_retries = 1`, `parallelism = 1`
- Both images built via `terraform_data` with `filemd5()` triggers (same pattern as vertexai-proxy in artifact-registry.tf)

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
