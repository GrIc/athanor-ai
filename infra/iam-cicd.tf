# CI/CD — Workload Identity Federation for GitHub Actions
# Allows GitHub Actions to authenticate as a GCP service account without any
# long-lived key. The OIDC token issued by GitHub is exchanged for a short-lived
# GCP access token via the WIF pool.

resource "google_iam_workload_identity_pool" "github" {
  workload_identity_pool_id = "github-pool"
  display_name              = "GitHub Actions"
  description               = "Pool for GitHub Actions OIDC authentication"
  depends_on                = [google_project_service.apis]
}

resource "google_iam_workload_identity_pool_provider" "github" {
  workload_identity_pool_id          = google_iam_workload_identity_pool.github.workload_identity_pool_id
  workload_identity_pool_provider_id = "github-provider"
  display_name                       = "GitHub OIDC"

  attribute_mapping = {
    "google.subject"       = "assertion.sub"
    "attribute.actor"      = "assertion.actor"
    "attribute.repository" = "assertion.repository"
  }

  # Only tokens from this specific repo are accepted
  attribute_condition = "assertion.repository == \"GrIc/athanor-ai\""

  oidc {
    issuer_uri = "https://token.actions.githubusercontent.com"
  }
}

resource "google_service_account" "cicd" {
  account_id   = "athanor-cicd"
  display_name = "Athanor CI/CD (GitHub Actions)"
  description  = "Used by GitHub Actions to run terraform apply and gcloud builds"
}

# Allow GitHub Actions OIDC tokens from this repo to impersonate the CI SA
resource "google_service_account_iam_member" "cicd_wif_binding" {
  service_account_id = google_service_account.cicd.name
  role               = "roles/iam.workloadIdentityUser"
  member             = "principalSet://iam.googleapis.com/${google_iam_workload_identity_pool.github.name}/attribute.repository/GrIc/athanor-ai"
}

# Permissions needed by the CI service account
resource "google_project_iam_member" "cicd_editor" {
  project = var.project_id
  role    = "roles/editor"
  member  = "serviceAccount:${google_service_account.cicd.email}"
}

# Billing read access (required for google_billing_account data source)
# Must be on the billing account itself, not the project
# Uses the variable directly to avoid circular dependency with the data source
resource "google_billing_account_iam_member" "cicd_billing_viewer" {
  billing_account_id = var.gcp_billing_account_id
  role               = "roles/billing.viewer"
  member             = "serviceAccount:${google_service_account.cicd.email}"
}

resource "google_project_iam_member" "cicd_secret_manager" {
  project = var.project_id
  role    = "roles/secretmanager.admin"
  member  = "serviceAccount:${google_service_account.cicd.email}"
}

resource "google_project_iam_member" "cicd_iam_admin" {
  project = var.project_id
  role    = "roles/resourcemanager.projectIamAdmin"
  member  = "serviceAccount:${google_service_account.cicd.email}"
}

resource "google_project_iam_member" "cicd_cloud_build" {
  project = var.project_id
  role    = "roles/cloudbuild.builds.editor"
  member  = "serviceAccount:${google_service_account.cicd.email}"
}

# GCS access for Terraform state
resource "google_storage_bucket_iam_member" "cicd_tfstate" {
  bucket = "athanor-ai-tfstate"
  role   = "roles/storage.objectAdmin"
  member = "serviceAccount:${google_service_account.cicd.email}"
}

# Outputs used to configure GitHub Actions secrets
output "wif_provider" {
  value       = google_iam_workload_identity_pool_provider.github.name
  description = "Set as GH secret WIF_PROVIDER"
}

output "cicd_service_account" {
  value       = google_service_account.cicd.email
  description = "Set as GH secret WIF_SERVICE_ACCOUNT"
}
