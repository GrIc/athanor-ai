# Athanor — Troubleshooting

## Cloud Run

### OpenWebUI won't start
- **OOM**: Increase memory to 1Gi or 2Gi in Terraform
- **Port mismatch**: Ensure `containerPort: 8080` matches OpenWebUI default
- **Missing env vars**: Check Secret Manager refs in Cloud Run config
- **Logs**: `gcloud run services logs read athanor-openwebui --region europe-west9 --limit 100`

### Cold start too slow (>30s)
- Enable `cpu-boost` in Cloud Run
- Consider `startup-cpu-boost` annotation
- If daily usage: set `min-instances: 1` (adds ~€15/month)

### GCS FUSE mount failure
- Check service account has `storage.objectAdmin` on the bucket
- Verify execution environment is Gen2 (`--execution-environment gen2`)
- Check bucket exists in correct region

## Terraform

### State lock
```bash
terraform force-unlock <LOCK_ID>
```

### Provider version conflict
```bash
terraform init -upgrade
```

### "Resource already exists"
- Import existing resource: `terraform import <resource_address> <resource_id>`
- Or delete manually and re-apply

## OpenRouter

### 401 Unauthorized
- Check API key in Secret Manager is current
- Verify key has credits: https://openrouter.ai/settings/credits

### Model not available
- Some models are intermittently unavailable
- Use `:floor` suffix for fallback to cheapest provider
- Check status: https://openrouter.ai/status

### Unexpected costs
- Check OpenRouter activity: https://openrouter.ai/activity
- Review which models are being used (Opus is 10x more expensive than Sonnet)
- Check for background tasks (auto-title, auto-tag) using expensive models

## OpenWebUI

### Can't create accounts
- Check `ENABLE_SIGNUP=true`
- Check `DEFAULT_USER_ROLE` — if `pending`, admin must approve

### RAG not working
- Ensure documents are uploaded and embedded (check admin panel)
- ChromaDB may need more memory — increase Cloud Run limits
- Check embedding model is configured (default: OpenAI-compatible via OpenRouter)

### Pipelines not loading
- Pipelines must be in the correct directory structure
- Check Python syntax errors in pipeline files
- Restart the Cloud Run service after adding pipelines