# Terraform Mode Rules — Athanor

## Conventions
- Provider: `google` + `google-beta`, pinned version in `infra/versions.tf`
- Backend: GCS bucket for remote state (`athanor-ai-tfstate`)
- Region: `europe-west9` (Paris) — hardcoded default
- Naming: `athanor-{component}-{env}` (e.g., `athanor-openwebui-prod`)

## Module Structure
```
infra/
├── main.tf              # Root module
├── variables.tf         # Root variables
├── outputs.tf           # Root outputs
├── versions.tf          # Provider + backend config
├── envs/
│   ├── prod.tfvars
│   └── dev.tfvars
└── modules/
    ├── cloud-run/       # Cloud Run service
    ├── gcs/             # GCS buckets
    ├── iam/             # Service accounts, IAM bindings
    ├── secrets/         # Secret Manager
    ├── monitoring/      # Budget alerts, uptime checks
    └── registry/        # Artifact Registry
```

## Labels — MANDATORY on every resource
```hcl
labels = {
  project     = "athanor"
  environment = var.environment
  managed_by  = "terraform"
}
```

## Patterns
- Cloud Run: always `min_instance_count = 0`
- Secrets: always via `google_secret_manager_secret_version`, never inline
- Budget alerts: 30%, 50%, 80%, 90%, 100% thresholds

## Validation Before Apply
1. `terraform fmt -check -recursive`
2. `terraform validate`
3. `terraform plan -var-file=envs/prod.tfvars`
4. Verify: no resources outside EU, all labels present, no plaintext secrets
