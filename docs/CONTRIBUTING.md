# Athanor — Contributing

## Language

- All code, comments, docs, commit messages, and PR descriptions: **English**
- This is an open-source project intended for international reuse

## Git Workflow

### Branch naming
```
feat/short-description
fix/short-description
infra/short-description
docs/short-description
```

### Commit messages (Conventional Commits)
```
feat: add OpenWebUI Cloud Run deployment
fix: correct GCS bucket region to europe-west9
infra: add budget alert Terraform module
docs: update architecture diagram
chore: bump OpenWebUI image tag
```

### PR process
1. Create feature branch from `main`
2. Make changes, commit atomically
3. Run `terraform validate` and `terraform fmt` for IaC changes
4. Open PR with description of what and why
5. Review (or self-review with Claude Code reviewer agent)
6. Squash and merge

## Code Standards

### Terraform
- `terraform fmt` on all `.tf` files
- Variables have descriptions and types
- Outputs documented
- Labels on every GCP resource

### Python (Pipelines)
- Format with `black`
- Lint with `ruff`
- Type hints on function signatures
- Docstrings on public functions

### Docker
- Multi-stage builds
- Non-root user
- Pinned base image tags
- HEALTHCHECK where applicable