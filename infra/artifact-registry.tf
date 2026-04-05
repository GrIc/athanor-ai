resource "google_artifact_registry_repository" "athanor_images" {
  location      = var.gcp_region
  repository_id = "athanor-images"
  format        = "DOCKER"
  labels        = var.labels
  depends_on    = [google_project_service.apis]
}

# Build l'image OpenWebUI via Cloud Build (dans GCP, pas en local)
# Re-déclenché si le Dockerfile change
resource "terraform_data" "build_openwebui_image" {
  triggers_replace = [
    google_artifact_registry_repository.athanor_images.id,
    filemd5("${path.module}/../docker/openwebui/Dockerfile"),
  ]

  provisioner "local-exec" {
    command = <<-EOT
      gcloud builds submit ${path.module}/../docker/openwebui \
        --tag ${var.gcp_region}-docker.pkg.dev/${var.project_id}/athanor-images/openwebui:latest \
        --project ${var.project_id}
    EOT
  }

  depends_on = [google_artifact_registry_repository.athanor_images]
}

# Build the VertexAI proxy image via Cloud Build
resource "terraform_data" "build_vertexai_proxy_image" {
  triggers_replace = [
    google_artifact_registry_repository.athanor_images.id,
    filemd5("${path.module}/../docker/vertexai-proxy/Dockerfile"),
    filemd5("${path.module}/../docker/vertexai-proxy/app.py"),
    filemd5("${path.module}/../docker/vertexai-proxy/requirements.txt"),
  ]

  provisioner "local-exec" {
    command = <<-EOT
      gcloud builds submit ${path.module}/../docker/vertexai-proxy \
        --tag ${var.gcp_region}-docker.pkg.dev/${var.project_id}/athanor-images/vertexai-proxy:latest \
        --project ${var.project_id}
    EOT
  }

  depends_on = [google_artifact_registry_repository.athanor_images]
}
