variable "project_id" {
  type        = string
  description = "GCP project ID"
}

variable "gcp_region" {
  type        = string
  description = "GCP region for all resources"
  default     = "europe-west9"
}

variable "openwebui_image" {
  type        = string
  description = "OpenWebUI Docker image"
  default     = "ghcr.io/open-webui/open-webui:main"
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

variable "labels" {
  type        = map(string)
  description = "Default labels for all resources"
  default = {
    project     = "athanor"
    env         = "prod"
    managed-by  = "terraform"
  }
}