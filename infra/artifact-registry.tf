resource "google_artifact_registry_repository" "athanor_images" {
  location      = var.gcp_region
  repository_id = "athanor-images"
  format        = "DOCKER"
  labels        = var.labels
  depends_on    = [google_project_service.apis]
}

# Build OpenWebUI image via Cloud Build (in GCP, not locally)
# Triggered if the Dockerfile changes
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

# Build the weekly digest image via Cloud Build
resource "terraform_data" "build_weekly_digest_image" {
  triggers_replace = [
    google_artifact_registry_repository.athanor_images.id,
    filemd5("${path.module}/../docker/weekly-digest/Dockerfile"),
    filemd5("${path.module}/../docker/weekly-digest/digest.py"),
    filemd5("${path.module}/../docker/weekly-digest/requirements.txt"),
  ]

  provisioner "local-exec" {
    command = <<-EOT
      gcloud builds submit ${path.module}/../docker/weekly-digest \
        --tag ${var.gcp_region}-docker.pkg.dev/${var.project_id}/athanor-images/weekly-digest:latest \
        --project ${var.project_id}
    EOT
  }

  depends_on = [google_artifact_registry_repository.athanor_images]
}

# Build the cost dashboard image via Cloud Build
resource "terraform_data" "build_cost_dashboard_image" {
  triggers_replace = [
    google_artifact_registry_repository.athanor_images.id,
    filemd5("${path.module}/../docker/cost-dashboard/Dockerfile"),
    filemd5("${path.module}/../docker/cost-dashboard/app.py"),
    filemd5("${path.module}/../docker/cost-dashboard/requirements.txt"),
  ]

  provisioner "local-exec" {
    command = <<-EOT
      gcloud builds submit ${path.module}/../docker/cost-dashboard \
        --tag ${var.gcp_region}-docker.pkg.dev/${var.project_id}/athanor-images/cost-dashboard:latest \
        --project ${var.project_id}
    EOT
  }

  depends_on = [google_artifact_registry_repository.athanor_images]
}

# Build the Athanor RAG image via Cloud Build
resource "terraform_data" "build_athanor_rag_image" {
  triggers_replace = [
    google_artifact_registry_repository.athanor_images.id,
    filemd5("${path.module}/../docker/athanor-rag/Dockerfile"),
    filemd5("${path.module}/../docker/athanor-rag/requirements.txt"),
    filemd5("${path.module}/../docker/athanor-rag/main.py"),
  ]

  provisioner "local-exec" {
    command = <<-EOT
      # Note: requires the build context to be the project root so we can include lib/
      gcloud builds submit ${path.module}/.. \
        --config ${path.module}/../docker/athanor-rag/cloudbuild.yaml \
        --project ${var.project_id} \
        --substitutions=_IMAGE_NAME=${var.gcp_region}-docker.pkg.dev/${var.project_id}/athanor-images/athanor-rag:latest
    EOT
  }

  depends_on = [google_artifact_registry_repository.athanor_images]
}

# Build the Athanor Ingest image via Cloud Build
resource "terraform_data" "build_athanor_ingest_image" {
  triggers_replace = [
    google_artifact_registry_repository.athanor_images.id,
    filemd5("${path.module}/../docker/athanor-ingest/Dockerfile"),
    filemd5("${path.module}/../docker/athanor-ingest/requirements.txt"),
    filemd5("${path.module}/../docker/athanor-ingest/ingest_job.py"),
  ]

  provisioner "local-exec" {
    command = <<-EOT
      # Note: requires the build context to be the project root so we can include lib/
      gcloud builds submit ${path.module}/.. \
        --config ${path.module}/../docker/athanor-ingest/cloudbuild.yaml \
        --project ${var.project_id} \
        --substitutions=_IMAGE_NAME=${var.gcp_region}-docker.pkg.dev/${var.project_id}/athanor-images/athanor-ingest:latest
    EOT
  }

  depends_on = [google_artifact_registry_repository.athanor_images]
}
