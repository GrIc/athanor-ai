variable "project_id" {
  type        = string
  description = "GCP project ID"
}

variable "gcp_billing_account_id" {
  type        = string
  description = "GCP Billing Account ID (e.g. XXXXXX-XXXXXX-XXXXXX)"
  sensitive   = true
}

variable "gcp_region" {
  type        = string
  description = "GCP region for all resources"
  default     = "europe-west9"
}

variable "openwebui_image" {
  type        = string
  description = "OpenWebUI image in Artifact Registry (built via gcloud builds submit)"
  default     = ""
}

variable "openrouter_api_key" {
  type        = string
  description = "OpenRouter API key"
  sensitive   = true
}

variable "webui_secret_key" {
  type        = string
  description = "OpenWebUI secret key for JWT signing"
  sensitive   = true
}

variable "cloud_run_max_instances" {
  type        = number
  description = "Max Cloud Run instances"
  default     = 1
}

variable "cloud_run_min_instances" {
  type        = number
  description = "Min Cloud Run instances (0 = scale to zero)"
  default     = 0
}

variable "vertexai_proxy_api_key" {
  type        = string
  description = "API key for the VertexAI proxy (used by OpenWebUI to authenticate)"
  sensitive   = true
}

# ─── Parental Monitoring ───────────────────────────────────────────────
variable "smtp_user" {
  type        = string
  description = "Gmail address for sending alerts and digests"
  default     = ""
}

variable "smtp_password" {
  type        = string
  description = "Gmail App Password for SMTP"
  sensitive   = true
  default     = ""
}

variable "monitored_user_emails" {
  type        = string
  description = "Comma-separated emails of child accounts to monitor"
  default     = ""
}

variable "parent_alert_email" {
  type        = string
  description = "Parent email address for receiving alerts and digests"
  default     = ""
}

# ─── Budget Tracking ───────────────────────────────────────────────────
variable "default_weekly_budget_eur" {
  type        = number
  description = "Default weekly budget per user (EUR)"
  default     = 2.0
}

variable "default_daily_budget_eur" {
  type        = number
  description = "Default daily budget per user (EUR)"
  default     = 0.50
}

variable "user_budget_overrides_json" {
  type        = string
  description = "Per-user budget overrides as JSON string"
  default     = "{}"
}

variable "budget_block_on_exceeded" {
  type        = bool
  description = "Block requests when budget is exceeded (or just warn)"
  default     = true
}

variable "labels" {
  type        = map(string)
  description = "Default labels for all resources"
  default = {
    project    = "athanor"
    env        = "prod"
    managed-by = "terraform"
  }
}
