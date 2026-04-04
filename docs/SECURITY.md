# Athanor — Security & Data Sovereignty

## IAM Strategy

### Service Accounts (Least Privilege)

| Service Account | Purpose | Roles |
|----------------|---------|-------|
| `openwebui-sa` | Cloud Run OpenWebUI | `run.invoker`, `secretmanager.secretAccessor`, `storage.objectAdmin` (on data bucket) |
| `langfuse-sa` | Cloud Run Langfuse | `run.invoker`, `secretmanager.secretAccessor` |
| `cicd-sa` | GitHub Actions deploy | `run.admin`, `artifactregistry.writer`, `iam.serviceAccountUser` |
| `monitoring-sa` | Budget alerts / Carbon | `billing.viewer`, `monitoring.viewer` |

### Principles
- No default service account usage — always create dedicated SAs
- No `roles/owner` or `roles/editor` on service accounts
- All IAM bindings in Terraform (`infra/modules/iam/`)

## Secret Manager

All secrets stored in GCP Secret Manager, mounted as env vars in Cloud Run:

| Secret name | Content | Consumers |
|-------------|---------|-----------|
| `openrouter-key` | OpenRouter API key | OpenWebUI |
| `webui-secret` | Session encryption key | OpenWebUI |
| `db-password` | PostgreSQL password | OpenWebUI (when migrated) |
| `langfuse-secret` | Langfuse encryption key | Langfuse |

### Rules
- NEVER put secrets in Terraform state → use `google_secret_manager_secret_version` with variable input
- NEVER commit secrets to git → `.gitignore` includes `*.tfvars` with real values
- Rotate secrets quarterly (manual for now, automate in Phase 4)

## Data Sovereignty

### Hosting
- All GCP resources in `europe-west9` (Paris) or `europe-west1` (Belgium)
- No data replication outside EU

### Data Flow Through LLM Providers
- Prompts transit through OpenRouter → LLM provider (Anthropic, OpenAI, etc.)
- OpenRouter privacy: prompts not stored (verify their current policy)
- For highly sensitive data: consider local models via Ollama on Cloud Run (GPU) or Raspberry Pi

### Proton Drive
- Source of truth for family documents (E2E encrypted)
- Never replicated outside the controlled pipeline: `Proton Drive → rclone → GCS bucket → RAG`
- GCS bucket encrypted with Google-managed keys (default) or CMEK (Phase 5)

## Parental Controls

### Available Mechanisms
1. **Model whitelisting**: restrict kids to free/low-cost models only
2. **Chat history retention**: `ENABLE_CHAT_DELETE=false` prevents deletion
3. **Toxic message filter**: Detoxify pipeline blocks harmful content
4. **Rate limiting**: cap requests per user per hour
5. **System prompts**: inject guardrails per model for child accounts
6. **Admin audit**: review conversation logs in admin panel

### Limitations
- OpenWebUI has no built-in content filtering (web safety) — complement with network-level tools (AdGuard Home, OpenWrt)
- No screen time controls — handle at device/OS level
- System prompt guardrails can be bypassed by determined users

## Network Security

- Cloud Run: public endpoint (no VPC needed for MVP)
- Authentication: handled by OpenWebUI's built-in auth (email/password)
- HTTPS: automatic via Cloud Run (Google-managed TLS certificate)
- Home Assistant: local only, exposed via Cloudflare Tunnel or Tailscale if needed