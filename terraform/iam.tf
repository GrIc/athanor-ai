data "google_project" "current" {}

# Grant Secret Manager access to default compute service account
resource "google_secret_manager_secret_iam_member" "openrouter_api_key_access" {
  secret_id = google_secret_manager_secret.openrouter_api_key.secret_id
  role      = "roles/secretmanager.secretAccessor"
  member    = "serviceAccount:${data.google_project.current.number}-compute@developer.gserviceaccount.com"
}

resource "google_secret_manager_secret_iam_member" "webui_secret_key_access" {
  secret_id = google_secret_manager_secret.webui_secret_key.secret_id
  role      = "roles/secretmanager.secretAccessor"
  member    = "serviceAccount:${data.google_project.current.number}-compute@developer.gserviceaccount.com"
}

# Grant GCS access to default compute service account
resource "google_storage_bucket_iam_member" "openwebui_data_access" {
  bucket = google_storage_bucket.openwebui_data.name
  role   = "roles/storage.objectAdmin"
  member = "serviceAccount:${data.google_project.current.number}-compute@developer.gserviceaccount.com"
}