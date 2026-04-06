# ─── Parental Monitoring ─────────────────────────────────────────────────────
# Weekly digest Cloud Run Job + Cloud Scheduler trigger.

locals {
  weekly_digest_image = "${var.gcp_region}-docker.pkg.dev/${var.project_id}/athanor-images/weekly-digest:latest"
}

# SMTP password for sending digest/alert emails via Gmail
resource "google_secret_manager_secret" "smtp_password" {
  secret_id = "athanor-smtp-password"
  labels    = var.labels

  replication {
    auto {}
  }
}

resource "google_secret_manager_secret_version" "smtp_password" {
  secret      = google_secret_manager_secret.smtp_password.id
  secret_data = var.smtp_password
}

resource "google_secret_manager_secret_iam_member" "smtp_password_access" {
  secret_id = google_secret_manager_secret.smtp_password.secret_id
  role      = "roles/secretmanager.secretAccessor"
  member    = "serviceAccount:${data.google_project.current.number}-compute@developer.gserviceaccount.com"
}

# Cloud Run Job — weekly parental digest
resource "google_cloud_run_v2_job" "weekly_digest" {
  name     = "athanor-weekly-digest"
  location = var.gcp_region
  labels   = var.labels

  depends_on = [
    terraform_data.build_weekly_digest_image,
    google_artifact_registry_repository_iam_member.cloudrun_agent_ar_access,
  ]

  template {
    template {
      containers {
        image = local.weekly_digest_image

        resources {
          limits = {
            memory = "512Mi"
            cpu    = "1"
          }
        }

        env {
          name  = "GCS_BUCKET"
          value = google_storage_bucket.openwebui_data.name
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
          name  = "MONITORED_USERS"
          value = var.monitored_user_emails
        }

        env {
          name  = "ALERT_EMAIL"
          value = var.parent_alert_email
        }

        env {
          name  = "SMTP_HOST"
          value = "smtp.gmail.com"
        }

        env {
          name  = "SMTP_PORT"
          value = "587"
        }

        env {
          name  = "SMTP_USER"
          value = var.smtp_user
        }

        env {
          name = "SMTP_PASSWORD"
          value_source {
            secret_key_ref {
              secret  = google_secret_manager_secret.smtp_password.id
              version = "latest"
            }
          }
        }
      }
    }
  }
}

# Cloud Scheduler — trigger digest every Sunday at 20:00 Paris time
resource "google_cloud_scheduler_job" "weekly_digest_trigger" {
  name      = "athanor-weekly-digest-trigger"
  schedule  = "0 20 * * 0" # Every Sunday at 20:00
  time_zone = "Europe/Paris"
  region    = var.gcp_region

  depends_on = [google_project_service.apis]

  http_target {
    uri         = "https://${var.gcp_region}-run.googleapis.com/apis/run.googleapis.com/v1/namespaces/${var.project_id}/jobs/${google_cloud_run_v2_job.weekly_digest.name}:run"
    http_method = "POST"

    oauth_token {
      service_account_email = "${data.google_project.current.number}-compute@developer.gserviceaccount.com"
    }
  }
}

# IAM — allow the default compute SA to invoke Cloud Run jobs
resource "google_project_iam_member" "compute_run_invoker" {
  project = var.project_id
  role    = "roles/run.invoker"
  member  = "serviceAccount:${data.google_project.current.number}-compute@developer.gserviceaccount.com"
}
