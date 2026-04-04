data "google_project" "current" {
  depends_on = [google_project_service.apis]
}

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

# Grant Artifact Registry read access to Cloud Run service agent (pulls images)
resource "google_artifact_registry_repository_iam_member" "cloudrun_agent_ar_access" {
  location   = google_artifact_registry_repository.athanor_images.location
  repository = google_artifact_registry_repository.athanor_images.name
  role       = "roles/artifactregistry.reader"
  member     = "serviceAccount:service-${data.google_project.current.number}@serverless-robot-prod.iam.gserviceaccount.com"
}

# Grant Artifact Registry read access to runtime compute service account
resource "google_artifact_registry_repository_iam_member" "openwebui_ar_access" {
  location   = google_artifact_registry_repository.athanor_images.location
  repository = google_artifact_registry_repository.athanor_images.name
  role       = "roles/artifactregistry.reader"
  member     = "serviceAccount:${data.google_project.current.number}-compute@developer.gserviceaccount.com"
}

# Grant GCS access to default compute service account
resource "google_storage_bucket_iam_member" "openwebui_data_access" {
  bucket = google_storage_bucket.openwebui_data.name
  role   = "roles/storage.objectAdmin"
  member = "serviceAccount:${data.google_project.current.number}-compute@developer.gserviceaccount.com"
}