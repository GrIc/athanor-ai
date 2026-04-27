resource "google_secret_manager_secret" "rclone_conf" {
  secret_id = "athanor-rclone-conf"
  labels    = var.labels
  replication {
    auto {}
  }
}

resource "google_secret_manager_secret_version" "rclone_conf" {
  secret      = google_secret_manager_secret.rclone_conf.id
  secret_data = var.rclone_conf
}

resource "google_secret_manager_secret" "rag_api_key" {
  secret_id = "athanor-rag-api-key"
  labels    = var.labels
  replication {
    auto {}
  }
}

resource "google_secret_manager_secret_version" "rag_api_key" {
  secret      = google_secret_manager_secret.rag_api_key.id
  secret_data = var.rag_api_key
}
