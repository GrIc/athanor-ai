output "openwebui_url" {
  value       = google_cloud_run_v2_service.openwebui.uri
  description = "OpenWebUI Cloud Run URL"
}

output "gcs_bucket_name" {
  value       = google_storage_bucket.openwebui_data.name
  description = "GCS bucket name for OpenWebUI data"
}

output "openwebui_service_name" {
  value       = google_cloud_run_v2_service.openwebui.name
  description = "Cloud Run service name"
}