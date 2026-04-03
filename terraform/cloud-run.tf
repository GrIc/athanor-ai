resource "google_cloud_run_v2_service" "openwebui" {
  name     = "athanor-openwebui"
  location = var.gcp_region
  labels   = var.labels

  template {
    max_instance_request_concurrency = 80
    scaling {
      min_instance_count = var.cloud_run_min_instances
      max_instance_count = var.cloud_run_max_instances
    }

    containers {
      image = var.openwebui_image

      ports {
        container_port = 8080
      }

      resources {
        limits = {
          memory = "1Gi"
          cpu    = "1"
        }
      }

      env {
        name  = "WEBUI_AUTH"
        value = "true"
      }

      env {
        name  = "WEBUI_URL"
        value = "https://athanor-openwebui-HASH.run.app" # Update after first deploy
      }

      env {
        name  = "OPENAI_API_BASE_URL"
        value = "https://openrouter.ai/api/v1"
      }

      env {
        name  = "PORT"
        value = "8080"
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