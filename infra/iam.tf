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

# Grant Artifact Registry read access at project level.
# Project-level grants are used instead of repo-level because the CI/CD SA has
# roles/resourcemanager.projectIamAdmin (can manage project IAM) but not
# artifactregistry.repositories.setIamPolicy (repo-level IAM) — avoids bootstrap problem.

# Cloud Run service agent — pulls images from Artifact Registry
resource "google_project_iam_member" "cloudrun_agent_ar_access" {
  project = var.project_id
  role    = "roles/artifactregistry.reader"
  member  = "serviceAccount:service-${data.google_project.current.number}@serverless-robot-prod.iam.gserviceaccount.com"
}

# Default compute service account — pulls images at runtime
resource "google_project_iam_member" "openwebui_ar_access" {
  project = var.project_id
  role    = "roles/artifactregistry.reader"
  member  = "serviceAccount:${data.google_project.current.number}-compute@developer.gserviceaccount.com"
}

# Grant GCS access to default compute service account
resource "google_storage_bucket_iam_member" "openwebui_data_access" {
  bucket = google_storage_bucket.openwebui_data.name
  role   = "roles/storage.objectAdmin"
  member = "serviceAccount:${data.google_project.current.number}-compute@developer.gserviceaccount.com"
}

# Grant VertexAI access to default compute service account
resource "google_project_iam_member" "openwebui_vertexai_access" {
  project = var.project_id
  role    = "roles/aiplatform.user"
  member  = "serviceAccount:${data.google_project.current.number}-compute@developer.gserviceaccount.com"
}

# Grant proxy access to the VertexAI proxy API key secret
resource "google_secret_manager_secret_iam_member" "vertexai_proxy_api_key_access" {
  secret_id = google_secret_manager_secret.vertexai_proxy_api_key.secret_id
  role      = "roles/secretmanager.secretAccessor"
  member    = "serviceAccount:${data.google_project.current.number}-compute@developer.gserviceaccount.com"
}
