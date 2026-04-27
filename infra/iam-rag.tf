resource "google_service_account" "rag_sa" {
  account_id   = "athanor-rag-sa"
  display_name = "Athanor RAG Service Account"
}

resource "google_storage_bucket_iam_member" "rag_data_admin" {
  bucket = google_storage_bucket.rag_data.name
  role   = "roles/storage.objectAdmin"
  member = "serviceAccount:${google_service_account.rag_sa.email}"
}

resource "google_storage_bucket_iam_member" "rag_backup_admin" {
  bucket = google_storage_bucket.rag_backup.name
  role   = "roles/storage.objectAdmin"
  member = "serviceAccount:${google_service_account.rag_sa.email}"
}

resource "google_project_iam_member" "rag_run_developer" {
  project = var.project_id
  role    = "roles/run.developer"
  member  = "serviceAccount:${google_service_account.rag_sa.email}"
}

resource "google_secret_manager_secret_iam_member" "rag_rclone_access" {
  secret_id = google_secret_manager_secret.rclone_conf.secret_id
  role      = "roles/secretmanager.secretAccessor"
  member    = "serviceAccount:${google_service_account.rag_sa.email}"
}

resource "google_secret_manager_secret_iam_member" "rag_api_key_access" {
  secret_id = google_secret_manager_secret.rag_api_key.secret_id
  role      = "roles/secretmanager.secretAccessor"
  member    = "serviceAccount:${google_service_account.rag_sa.email}"
}

# Also grant access to the VertexAI proxy key (referenced in cloud-run-rag.tf)
# NOTE: google_secret_manager_secret.vertexai_proxy_api_key is actually used in infra/cloud-run.tf
# The secret_id is typically "athanor-vertexai-proxy-api-key", but let's use the resource name.
resource "google_secret_manager_secret_iam_member" "rag_vertexai_key_access" {
  secret_id = google_secret_manager_secret.vertexai_proxy_api_key.secret_id
  role      = "roles/secretmanager.secretAccessor"
  member    = "serviceAccount:${google_service_account.rag_sa.email}"
}
