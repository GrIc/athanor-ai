# ─── FinOps: BigQuery Billing Export + Carbon Footprint ──────────────────────

# BigQuery dataset for billing data export
resource "google_bigquery_dataset" "billing_export" {
  dataset_id                 = "athanor_billing_export"
  friendly_name              = "Athanor Billing Data Export"
  description                = "GCP billing data exported to BigQuery for cost analysis"
  location                   = "EU" # Must be EU for europe-west9 compliance
  delete_contents_on_destroy = false
  labels                     = var.labels
}

# BigQuery dataset for carbon footprint data
resource "google_bigquery_dataset" "carbon_footprint" {
  dataset_id                 = "athanor_carbon_footprint"
  friendly_name              = "Athanor Carbon Footprint"
  description                = "GCP carbon footprint data for sustainability reporting"
  location                   = "EU"
  delete_contents_on_destroy = false
  labels                     = var.labels
}

# IAM — allow billing service account to write to billing dataset
resource "google_project_iam_member" "billing_bigquery_writer" {
  project = var.project_id
  role    = "roles/bigquery.dataEditor"
  member  = "serviceAccount:billing-export-service-account@${var.project_id}.iam.gserviceaccount.com"
}

# Note: The actual billing export must be configured via the GCP Console or API.
# Terraform does not support creating billing account-level exports directly.
# After applying, run:
#   gcloud alpha billing accounts export bigquery \
#     --billing-account=${BILLING_ACCOUNT_ID} \
#     --bigquery-dataset=athanor_billing_export \
#     --bigquery-table=cloud_billing \
#     --resource-usage
