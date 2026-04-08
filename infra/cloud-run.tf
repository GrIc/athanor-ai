locals {
  openwebui_image      = var.openwebui_image != "" ? var.openwebui_image : "${var.gcp_region}-docker.pkg.dev/${var.project_id}/athanor-images/openwebui:latest"
  vertexai_proxy_image = "${var.gcp_region}-docker.pkg.dev/${var.project_id}/athanor-images/vertexai-proxy:latest"
  cost_dashboard_image = "${var.gcp_region}-docker.pkg.dev/${var.project_id}/athanor-images/cost-dashboard:latest"
}

resource "google_cloud_run_v2_service" "openwebui" {
  name     = "athanor-openwebui"
  location = var.gcp_region
  labels   = var.labels

  depends_on = [
    terraform_data.build_openwebui_image,
    google_project_iam_member.cloudrun_agent_ar_access,
    google_project_iam_member.openwebui_ar_access,
  ]

  template {
    max_instance_request_concurrency = 80
    scaling {
      min_instance_count = var.cloud_run_min_instances
      max_instance_count = var.cloud_run_max_instances
    }

    containers {
      image = local.openwebui_image

      ports {
        container_port = 8080
      }

      resources {
        limits = {
          memory = "1Gi"
          cpu    = "1"
        }
      }

      # OpenWebUI needs time to run DB migrations on first start
      startup_probe {
        http_get {
          path = "/health"
          port = 8080
        }
        initial_delay_seconds = 10
        period_seconds        = 10
        failure_threshold     = 30 # 10 + 30*10 = ~5min30s total
        timeout_seconds       = 5
      }

      env {
        name  = "WEBUI_AUTH"
        value = "true"
      }

      env {
        name  = "WEBUI_URL"
        value = "https://athanor-openwebui-${data.google_project.current.number}-${var.gcp_region}.a.run.app"
      }

      env {
        name  = "OPENAI_API_BASE_URL"
        value = "https://openrouter.ai/api/v1"
      }

      env {
        name = "OPENAI_API_KEY"
        value_source {
          secret_key_ref {
            secret  = google_secret_manager_secret.openrouter_api_key.id
            version = "latest"
          }
        }
      }

      env {
        name = "WEBUI_SECRET_KEY"
        value_source {
          secret_key_ref {
            secret  = google_secret_manager_secret.webui_secret_key.id
            version = "latest"
          }
        }
      }

      volume_mounts {
        mount_path = "/app/backend/data"
        name       = "openwebui-data"
      }
    }

    volumes {
      name = "openwebui-data"
      gcs {
        bucket    = google_storage_bucket.openwebui_data.name
        read_only = false
      }
    }
  }
}

resource "google_secret_manager_secret" "openrouter_api_key" {
  secret_id = "athanor-openrouter-api-key"
  labels    = var.labels

  replication {
    auto {}
  }
}

resource "google_secret_manager_secret_version" "openrouter_api_key" {
  secret      = google_secret_manager_secret.openrouter_api_key.id
  secret_data = var.openrouter_api_key
}

resource "google_secret_manager_secret" "webui_secret_key" {
  secret_id = "athanor-webui-secret-key"
  labels    = var.labels

  replication {
    auto {}
  }
}

resource "google_secret_manager_secret_version" "webui_secret_key" {
  secret      = google_secret_manager_secret.webui_secret_key.id
  secret_data = var.webui_secret_key
}

resource "google_cloud_run_v2_service_iam_member" "public_access" {
  location = google_cloud_run_v2_service.openwebui.location
  name     = google_cloud_run_v2_service.openwebui.name
  role     = "roles/run.invoker"
  member   = "allUsers"
}

# ─── VertexAI Proxy ──────────────────────────────────────────────────────

resource "google_cloud_run_v2_service" "vertexai_proxy" {
  name     = "athanor-vertexai-proxy"
  location = var.gcp_region
  labels   = var.labels

  depends_on = [
    terraform_data.build_vertexai_proxy_image,
    google_project_iam_member.cloudrun_agent_ar_access,
    google_project_iam_member.openwebui_ar_access,
  ]

  template {
    max_instance_request_concurrency = 1
    scaling {
      min_instance_count = 0
      max_instance_count = 1
    }

    containers {
      image = local.vertexai_proxy_image

      ports {
        container_port = 8080
      }

      startup_probe {
        http_get {
          path = "/health"
          port = 8080
        }
        initial_delay_seconds = 5
        period_seconds        = 10
        failure_threshold     = 6 # 5 + 6*10 = ~65s total
        timeout_seconds       = 5
      }

      resources {
        limits = {
          memory = "512Mi"
          cpu    = "1"
        }
      }

      env {
        name  = "VERTEXAI_PROJECT_ID"
        value = var.project_id
      }

      env {
        name  = "VERTEXAI_LOCATION"
        value = var.gcp_region
      }

      env {
        name = "PROXY_API_KEY"
        value_source {
          secret_key_ref {
            secret  = google_secret_manager_secret.vertexai_proxy_api_key.id
            version = "latest"
          }
        }
      }
    }
  }
}

resource "google_secret_manager_secret" "vertexai_proxy_api_key" {
  secret_id = "athanor-vertexai-proxy-api-key"
  labels    = var.labels

  replication {
    auto {}
  }
}

resource "google_secret_manager_secret_version" "vertexai_proxy_api_key" {
  secret      = google_secret_manager_secret.vertexai_proxy_api_key.id
  secret_data = var.vertexai_proxy_api_key
}

# Public access — Cloud Run IAM layer bypassed; app-level auth via PROXY_API_KEY.
# OpenWebUI cannot attach OIDC tokens to outbound HTTP calls, so allUsers is
# required here. The PROXY_API_KEY env var provides the real access control.
resource "google_cloud_run_v2_service_iam_member" "vertexai_proxy_public_access" {
  location = google_cloud_run_v2_service.vertexai_proxy.location
  name     = google_cloud_run_v2_service.vertexai_proxy.name
  role     = "roles/run.invoker"
  member   = "allUsers"
}

# ─── Cost Dashboard ──────────────────────────────────────────────────────

resource "google_cloud_run_v2_service" "cost_dashboard" {
  name     = "athanor-cost-dashboard"
  location = var.gcp_region
  labels   = var.labels

  depends_on = [
    terraform_data.build_cost_dashboard_image,
    google_project_iam_member.cloudrun_agent_ar_access,
    google_project_iam_member.openwebui_ar_access,
  ]

  template {
    max_instance_request_concurrency = 80
    scaling {
      min_instance_count = 0 # scale-to-zero
      max_instance_count = 1
    }

    containers {
      image = local.cost_dashboard_image

      ports {
        container_port = 8080
      }

      resources {
        limits = {
          memory = "256Mi"
          cpu    = "0.5"
        }
      }

      env {
        name  = "GCS_BUCKET"
        value = google_storage_bucket.openwebui_data.name
      }

      env {
        name  = "PROJECT_ID"
        value = var.project_id
      }
    }
  }
}

resource "google_cloud_run_v2_service_iam_member" "cost_dashboard_public_access" {
  location = google_cloud_run_v2_service.cost_dashboard.location
  name     = google_cloud_run_v2_service.cost_dashboard.name
  role     = "roles/run.invoker"
  member   = "allUsers"
}
