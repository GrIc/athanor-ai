# Debug Mode Rules — Athanor

## Methodology
1. **Reproduce first** — confirm the issue before proposing a fix
2. **Read logs** — always check Cloud Run logs or Terraform output first
3. **Narrow scope** — identify the specific component (Cloud Run, Terraform, OpenWebUI, OpenRouter)
4. **One hypothesis at a time** — test, confirm/deny, then move to the next

## Common Debug Paths

### Cloud Run issues
```bash
gcloud run services logs read athanor-openwebui --region europe-west9 --limit 50
gcloud run services describe athanor-openwebui --region europe-west9
```

### Terraform issues
```bash
terraform -chdir=infra plan -var-file=envs/prod.tfvars 2>&1 | head -100
terraform -chdir=infra state list
```

### OpenRouter connectivity
```bash
curl -s -H "Authorization: Bearer $OPENROUTER_KEY" https://openrouter.ai/api/v1/models | head -20
```

## Rules
- Don't guess — verify with actual commands and logs
- Don't fix more than the reported issue
- Propose the minimal fix, explain why it works
