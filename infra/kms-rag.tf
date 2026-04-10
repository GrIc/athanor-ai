resource "google_kms_key_ring" "rag" {
  name     = "athanor-rag-keyring"
  location = "europe-west9"
}

resource "google_kms_crypto_key" "rag_data" {
  name            = "athanor-rag-data-key"
  key_ring        = google_kms_key_ring.rag.id
  rotation_period = "7776000s" # 90 days
  labels          = var.labels
}

# Grant GCS service account access to use the key
resource "google_kms_crypto_key_iam_member" "gcs_kms" {
  crypto_key_id = google_kms_crypto_key.rag_data.id
  role          = "roles/cloudkms.cryptoKeyEncrypterDecrypter"
  member        = "serviceAccount:service-${data.google_project.current.number}@gs-project-accounts.iam.gserviceaccount.com"
}
