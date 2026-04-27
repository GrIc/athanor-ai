resource "google_cloud_run_v2_service" "athanor_rag" {
  name     = "athanor-rag"
  location = var.gcp_region
  labels   = var.labels

  template {
    service_account = google_service_account.rag_sa.email

    scaling {
      min_instance_count = 0
      max_instance_count = 1
    }

    containers {
      image = "${var.gcp_region}-docker.pkg.dev/${var.project_id}/athanor-images/athanor-rag:latest"

      resources {
        limits            = { memory = "2Gi", cpu = "1" }
        startup_cpu_boost = true
      }

      env {
        name  = "RAG_GCS_BUCKET"
        value = google_storage_bucket.rag_data.name
      }
      env {
        name  = "VERTEXAI_PROXY_URL"
        value = google_cloud_run_v2_service.vertexai_proxy.uri
      }
      env {
        name  = "INGEST_JOB_NAME"
        value = "projects/${var.project_id}/locations/${var.gcp_region}/jobs/athanor-ingest"
      }
      env {
        name  = "GCP_PROJECT_ID"
        value = var.project_id
      }
      env {
        name  = "GCP_REGION"
        value = var.gcp_region
      }
      env {
        name = "VERTEXAI_PROXY_KEY"
        value_source {
          secret_key_ref {
            secret  = google_secret_manager_secret.vertexai_proxy_api_key.secret_id
            version = "latest"
          }
        }
      }
      env {
        name = "RAG_API_KEY"
        value_source {
          secret_key_ref {
            secret  = google_secret_manager_secret.rag_api_key.secret_id
            version = "latest"
          }
        }
      }

      startup_probe {
        http_get { path = "/health" }
        initial_delay_seconds = 15
        period_seconds        = 10
        failure_threshold     = 18 # 3 minutes total
      }
    }
  }
}

resource "google_cloud_run_v2_service_iam_member" "rag_public" {
  name     = google_cloud_run_v2_service.athanor_rag.name
  location = var.gcp_region
  role     = "roles/run.invoker"
  member   = "allUsers" # Auth handled by RAG_API_KEY Bearer token
}

resource "google_cloud_run_v2_job" "athanor_ingest" {
  name     = "athanor-ingest"
  location = var.gcp_region
  labels   = var.labels

  template {
    template {
      service_account = google_service_account.rag_sa.email
      max_retries     = 1

      containers {
        image = "${var.gcp_region}-docker.pkg.dev/${var.project_id}/athanor-images/athanor-ingest:latest"

        resources { limits = { memory = "2Gi", cpu = "1" } }

        env {
          name  = "CONNECTOR_TYPE"
          value = var.connector_type
        }
        env {
          name  = "PROTON_DRIVE_ROOT"
          value = var.proton_drive_root
        }
        env {
          name  = "RAG_GCS_BUCKET"
          value = google_storage_bucket.rag_data.name
        }
        env {
          name  = "RAG_GCS_BACKUP_BUCKET"
          value = google_storage_bucket.rag_backup.name
        }
        env {
          name  = "VERTEXAI_PROXY_URL"
          value = google_cloud_run_v2_service.vertexai_proxy.uri
        }
        env {
          name  = "OCR_MODEL"
          value = var.ocr_model
        }
        env {
          name  = "EMBED_MODEL"
          value = var.embed_model
        }
        env {
          name  = "GCP_PROJECT_ID"
          value = var.project_id
        }
        env {
          name  = "GCP_REGION"
          value = var.gcp_region
        }
        env {
          name  = "RCLONE_CONFIG_SECRET"
          value = google_secret_manager_secret.rclone_conf.secret_id
        }
        env {
          name = "VERTEXAI_PROXY_KEY"
          value_source {
            secret_key_ref {
              secret  = google_secret_manager_secret.vertexai_proxy_api_key.secret_id
              version = "latest"
            }
          }
        }
      }
    }
  }
}

# Cloud Scheduler — europe-west1 (scheduler not available in europe-west9)
resource "google_cloud_scheduler_job" "athanor_ingest_trigger" {
  name      = "athanor-ingest-daily"
  region    = "europe-west1"
  schedule  = "0 3 * * *"
  time_zone = "Europe/Paris"

  http_target {
    http_method = "POST"
    uri         = "https://${var.gcp_region}-run.googleapis.com/apis/run.googleapis.com/v1/namespaces/${var.project_id}/jobs/athanor-ingest:run"

    oauth_token {
      service_account_email = google_service_account.rag_sa.email
    }
  }
}
