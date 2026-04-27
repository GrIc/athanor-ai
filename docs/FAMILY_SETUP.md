# Athanor — Family Setup Guide

> Manual setup guide for family accounts and OpenWebUI filters.

---

## 1. Create Family Accounts in OpenWebUI

1. Access the OpenWebUI URL: `https://athanor-openwebui-<PROJECT_NUMBER>-europe-west9.a.run.app`
2. Log in with the admin account (first account created on initial access)
3. Go to **Admin Panel** (gear icon > Admin Settings)
4. Tab **Users** > **Create User**
5. Create one account per family member:
   - **Parent 1**: email, password, role `user`
   - **Parent 2**: email, password, role `user`
   - **Child 1**: email, password, role `user`
   - **Child 2**: email, password, role `user`

> **Note**: OpenWebUI does not yet support native "parent/child" roles. Monitoring is done via emails configured in filters.

---

## 2. Configure Allowed Models (Model Whitelisting)

1. In **Admin Panel** > **Models**
2. For each user, you can restrict available models via **Model Filters**
3. Recommendation for teenagers:
   - ✅ Allow: `gemini-2.5-flash-lite`, `gemini-2.0-flash`, `openrouter/llama-3-70b`
   - ❌ Block: `gpt-4`, `claude-3.5-sonnet`, `claude-3-opus` (too expensive)

---

## 3. Enable Parental Monitor Filter

1. Go to **Admin Panel** > **Functions**
2. Click **Upload Function** (or **+ Create**)
3. Copy the content of [`pipelines/filters/parental_monitor.py`](../pipelines/filters/parental_monitor.py)
4. Once uploaded, enable the filter as a **Global Filter**
5. Configure the **Valves** in the UI:

| Valve | Value | Description |
|-------|--------|-------------|
| `monitored_emails` | `child1@gmail.com,child2@gmail.com` | Email addresses of monitored child accounts |
| `alert_email` | `parent@gmail.com` | Parent email address to receive alerts |
| `smtp_host` | `smtp.gmail.com` | SMTP server |
| `smtp_port` | `587` | SMTP port (TLS) |
| `smtp_user` | `your-gmail@gmail.com` | Gmail address for sending |
| `smtp_password` | `xxxx-xxxx-xxxx-xxxx` | Gmail App Password (not your main password) |
| `enabled` | `true` | Enable the filter |

> **Gmail App Password**: Create at [Google Account > App Passwords](https://myaccount.google.com/apppasswords). Requires 2‑step verification enabled.

---

## 4. Enable Budget Tracker Filter

1. Still in **Admin Panel** > **Functions**
2. Upload the file [`pipelines/filters/budget_tracker.py`](../pipelines/filters/budget_tracker.py)
3. Enable as **Global Filter** (must be **before** Parental Monitor in execution order)
4. Configure the **Valves**:

| Valve | Default Value | Description |
|-------|-------------------|-------------|
| `default_weekly_budget_eur` | `2.0` | Weekly budget per user (€) |
| `default_daily_budget_eur` | `0.50` | Daily budget per user (€) |
| `user_budgets_json` | `{}` | Per‑user overrides: `{"child1@gmail.com": {"weekly": 3.0, "daily": 0.75}}` |
| `openrouter_api_key` | `sk-or-v1-...` | OpenRouter API key (for fetching prices) |
| `block_on_exceeded` | `true` | Block or just warn when budget exceeded |
| `price_refresh_hours` | `24` | How often to refresh prices (hours) |
| `enabled` | `true` | Enable the filter |

> **Filter order**: Budget Tracker must run **before** Parental Monitor to block the request before content scanning.

---

## 5. Test the Weekly Digest

The weekly digest is a Cloud Run Job triggered every Sunday at 20:00 (Europe/Paris).

**Manual test**:
```bash
# Trigger the job now
gcloud run jobs run athanor-weekly-digest --region=europe-west9
```

**Check logs**:
```bash
gcloud run jobs executions list --job=athanor-weekly-digest --region=europe-west9 --limit=1
gcloud run jobs executions logs --region=europe-west9
```

---

## 6. Configure BigQuery Billing Export (one‑time)

After `terraform apply`, enable billing export to BigQuery:

```bash
# Replace with your billing account ID
BILLING_ACCOUNT_ID="XXXXXX-XXXXXX-XXXXXX"

gcloud alpha billing accounts export bigquery \
  --billing-account=${BILLING_ACCOUNT_ID} \
  --bigquery-dataset=athanor_billing_export \
  --bigquery-table=cloud_billing \
  --resource-usage
```

> **Note**: This command requires `billing.admin` permissions on the billing account.

---

## 7. Check GCP Budget

Budget alerts are configured in [`infra/budget.tf`](../infra/budget.tf):
- 30%, 50%, 80%, 90%, 100% of monthly budget
- Email notifications

To change the monthly budget, update `infra/envs/prod.tfvars`:
```hcl
monthly_budget_amount = 50  # EUR
```

---

## Validation Checklist

- [ ] 4 family accounts created (2 parents + 2 children)
- [ ] Models restricted for teenagers (Flash only)
- [ ] Parental Monitor enabled + SMTP alerts working
- [ ] Budget Tracker enabled + blocking at €2/week
- [ ] Weekly Digest tested manually
- [ ] BigQuery Billing Export configured
- [ ] Mobile PWA access tested
