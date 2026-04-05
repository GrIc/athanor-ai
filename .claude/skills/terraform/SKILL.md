---
name: terraform
description: >
  GCP Terraform IaC for the Athanor project. Use when working on infra/,
  creating or modifying GCP resources, writing Terraform modules, or
  planning infrastructure changes. Covers Cloud Run, GCS, IAM, Secret
  Manager, Artifact Registry, Budget Alerts, WIF.
tools: Read, Edit, Write, Bash, Glob, Grep
---

# Terraform Skill — Athanor Project

## Project Conventions

- **Provider**: `google`, pinned version in `infra/providers.tf`
- **Backend**: GCS bucket (`athanor-ai-tfstate`, prefix `terraform/state`)
- **Region**: `europe-west9` (Paris) — hardcoded default
- **Naming**: `athanor-{component}` (e.g., `athanor-openwebui`, `athanor-vertexai-proxy`)
- **Labels on EVERY resource**: `var.labels`
- **CI/CD**: GitHub Actions + Workload Identity Federation (no long-lived keys)

## File Structure (flat)

```
infra/
├── providers.tf          # google provider + GCS backend
├── apis.tf               # GCP API enablement
├── variables.tf          # Root variables
├── outputs.tf            # Service URLs, bucket names, WIF values
├── cloud-run.tf          # OpenWebUI + VertexAI Proxy + secrets
├── gcs.tf                # GCS buckets (data)
├── iam.tf                # Service account permissions
├── iam-cicd.tf           # WIF pool + CI service account
├── artifact-registry.tf  # Container registry + Cloud Build triggers
├── budget.tf             # Budget alerts
└── envs/
    ├── prod.tfvars           # Non-secret variables
    └── .env.prod.example     # Secret env vars template (local only)
```

## Key Patterns

### Cloud Run — Scale-to-Zero
```hcl
scaling {
  min_instance_count = 0   # MANDATORY
  max_instance_count = 1   # Cost cap
}
```

### Image builds — automatic on code change
```hcl
resource "terraform_data" "build_vertexai_proxy_image" {
  triggers_replace = [
    filemd5("${path.module}/../docker/vertexai-proxy/app.py"),
    # ... other source files
  ]
  provisioner "local-exec" {
    command = "gcloud builds submit ... --tag ..."
  }
}
```

### Secrets — Never Inline
```hcl
resource "google_secret_manager_secret_version" "api_key" {
  secret      = google_secret_manager_secret.my_key.id
  secret_data = var.my_api_key  # Passed via tfvars or CI/CD secrets
}
```

## Validation Checklist

1. `terraform fmt -check -recursive`
2. `terraform validate`
3. `terraform plan -var-file=envs/prod.tfvars`
4. No resources outside `europe-west9` / `europe-west1`
5. All resources have labels
6. No secrets in plaintext
