resource "google_storage_bucket" "rag_data" {
  name          = "athanor-ai-rag-data"
  location      = "europe-west9"
  storage_class = "STANDARD"
  labels        = var.labels

  versioning { enabled = false } # Snapshots are overwritten in-place; backup bucket handles recovery

  encryption {
    default_kms_key_name = google_kms_crypto_key.rag_data.id
  }

  lifecycle_rule {
    condition { age = 1 } # Clean up incomplete multipart uploads
    action { type = "AbortIncompleteMultipartUpload" }
  }
}

resource "google_storage_bucket" "rag_backup" {
  name          = "athanor-ai-rag-backup"
  location      = "europe-west9"
  storage_class = "NEARLINE"
  labels        = var.labels

  versioning { enabled = false }

  encryption {
    default_kms_key_name = google_kms_crypto_key.rag_data.id
  }

  lifecycle_rule {
    condition { age = 90 }
    action { type = "Delete" }
  }
}
