resource "google_project_service" "apis" {
  for_each = toset([
    "cloudresourcemanager.googleapis.com",
    "cloudbilling.googleapis.com",
    "billingbudgets.googleapis.com",
    "run.googleapis.com",
    "secretmanager.googleapis.com",
    "storage.googleapis.com",
    "iam.googleapis.com",
    "artifactregistry.googleapis.com",
    "aiplatform.googleapis.com",
    "cloudscheduler.googleapis.com",
    # Carbon Footprint API
    "cloudcarbonfootprint.googleapis.com",
    # BigQuery
    "bigquery.googleapis.com",
    "bigquerydatatransfer.googleapis.com",
  ])

  service            = each.key
  disable_on_destroy = false
}
