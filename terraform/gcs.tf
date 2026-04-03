resource "google_storage_bucket" "openwebui_data" {
  name                        = "${var.project_id}-athanor-data"
  location                    = var.gcp_region
  storage_class               = "STANDARD"
  uniform_bucket_level_access = true
  force_destroy               = false
  labels                      = var.labels

  versioning {
    enabled = true
  }

  lifecycle_rule {
    action {
      type = "Delete"
    }
    condition {
      age                   = 90
      matches_storage_class = ["NEARLINE"]
    }
  }
}