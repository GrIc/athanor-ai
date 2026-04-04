# Code Mode Rules — Athanor

## Terraform (infra/)
- `terraform fmt` before every commit
- All variables must have `description` and `type`
- Labels on EVERY GCP resource: `project`, `environment`, `managed_by`
- Use modules in `infra/modules/` — never inline complex resources in `main.tf`
- Cloud Run: always `min_instance_count = 0` (scale-to-zero)

## Python (pipelines/, scripts/)
- Format: `black`
- Lint: `ruff`
- Type hints on all function signatures
- Docstrings on public functions

## Docker (docker/)
- Multi-stage builds
- Non-root user (`USER 1001`)
- Pinned base image tags — never `:latest` in production
- HEALTHCHECK instruction

## Git
- Atomic commits with conventional commit messages
- Never commit `.tfvars` with real secrets

## Testing
- `terraform validate` + `terraform plan` before any apply
- For Python: pytest with basic coverage
