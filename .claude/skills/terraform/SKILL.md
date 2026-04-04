---
name: terraform
description: >
  GCP Terraform IaC for the Athanor project. Use when working on infra/,
  creating or modifying GCP resources, writing Terraform modules, or
  planning infrastructure changes. Covers Cloud Run, GCS, IAM, Secret
  Manager, Cloud SQL, Artifact Registry, Budget Alerts.
tools: Read, Edit, Write, Bash, Glob, Grep
---

# Terraform Skill — Athanor Project

## Project Conventions

- **Provider**: `google` and `google-beta`, pinned version in `infra/versions.tf`
- **Backend**: GCS bucket for remote state (`athanor-ai-tfstate`)
- **Region**: `europe-west9` (Paris) — hardcoded as default, never US
- **Naming**: `athanor-{component}-{env}` (e.g., `athanor-openwebui-prod`)
- **Labels on EVERY resource**:
  ```hcl
  labels = {
    project     = "athanor"
    environment = var.environment
    managed_by  = "terraform"
  }
  ```

## Module Structure

```
infra/
├── main.tf              # Root module, calls child modules
├── variables.tf         # Root variables
├── outputs.tf           # Root outputs
├── versions.tf          # Provider + backend config
├── envs/
│   ├── prod.tfvars
│   └── dev.tfvars
└── modules/
    ├── cloud-run/       # Cloud Run service definition
    ├── gcs/             # GCS buckets
    ├── iam/             # Service accounts, IAM bindings
    ├── secrets/         # Secret Manager secrets
    ├── monitoring/      # Budget alerts, uptime checks
    └── registry/        # Artifact Registry
```

## Key Patterns

### Cloud Run — Scale-to-Zero

```hcl
# IMPORTANT: Always set these for zero-cost-at-rest
scaling {
  min_instance_count = 0   # Scale to zero!
  max_instance_count = 2   # Cost cap
}
```

### Secrets — Never Inline

```hcl
# Always reference secrets via Secret Manager
resource "google_secret_manager_secret_version" "api_key" {
  secret      = google_secret_manager_secret.openrouter_key.id
  secret_data = var.openrouter_api_key  # Passed via tfvars or CI/CD
}
```

### Budget Alerts — Day 1

```hcl
resource "google_billing_budget" "monthly" {
  billing_account = var.billing_account_id
  display_name    = "athanor-monthly-budget"
  amount { specified_amount { currency_code = "EUR"; units = "50" } }
  threshold_rules { threshold_percent = 0.5 }   # 50%
  threshold_rules { threshold_percent = 0.8 }   # 80%
  threshold_rules { threshold_percent = 1.0 }   # 100%
}
```

## Validation Checklist

Before applying any Terraform change:

1. `terraform fmt -check -recursive`
2. `terraform validate`
3. `terraform plan -var-file=envs/prod.tfvars` — review the plan
4. Confirm no resources are created outside `europe-west9` / `europe-west1`
5. Confirm all resources have the required labels
6. Confirm no secrets are in plaintext
