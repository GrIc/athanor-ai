data "google_billing_account" "account" {
  display_name = "${var.gcp_billing_account_name}"
  open         = true
}

resource "google_billing_budget" "monthly_budget" {
  display_name = "Athanor Monthly Budget"
  billing_account = data.google_billing_account.account.id

  budget_filter {
    projects = ["projects/${var.project_id}"]
    credit_types_treatment = "EXCLUDE_ALL_CREDITS"
  }

  amount {
    specified_amount {
      currency_code = "EUR"
      units        = "30"
    }
  }

  threshold_rules {
    threshold_percent = 0.3
    spend_basis       = "CURRENT_SPEND"
  }

  threshold_rules {
    threshold_percent = 0.5
    spend_basis       = "CURRENT_SPEND"
  }

  threshold_rules {
    threshold_percent = 0.8
    spend_basis       = "CURRENT_SPEND"
  }

  threshold_rules {
    threshold_percent = 0.9
    spend_basis       = "CURRENT_SPEND"
  }

  threshold_rules {
    threshold_percent = 1.0
    spend_basis       = "CURRENT_SPEND"
  }
}