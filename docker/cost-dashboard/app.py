"""Cost Dashboard — Cloud Run service.

Serves a simple HTML dashboard showing per-user cost tracking data.
Reads from GCS (budget_usage.json) and optionally from BigQuery billing export.

Deploy:
  gcloud builds submit --tag=europe-west9-docker.pkg.dev/athanor-ai/athanor-images/cost-dashboard:latest docker/cost-dashboard/
  gcloud run deploy athanor-cost-dashboard \
    --image=europe-west9-docker.pkg.dev/athanor-ai/athanor-images/cost-dashboard:latest \
    --region=europe-west9 \
    --allow-unauthenticated \
    --min-instances=0 \
    --max-instances=1
"""

import json
import os
from datetime import datetime, timezone
from pathlib import Path

from flask import Flask, render_template_string
from google.cloud import storage

app = Flask(__name__)

GCS_BUCKET = os.environ.get("GCS_BUCKET", "athanor-openwebui-data")
PROJECT_ID = os.environ.get("PROJECT_ID", "athanor-ai")

# HTML Template
DASHBOARD_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>Athanor — Cost Dashboard</title>
    <style>
        body { font-family: -apple-system, BlinkMacSystemFont, sans-serif; max-width: 900px; margin: 0 auto; padding: 20px; background: #f5f5f5; }
        h1 { color: #333; }
        .card { background: white; border-radius: 8px; padding: 20px; margin: 15px 0; box-shadow: 0 1px 3px rgba(0,0,0,0.1); }
        .card h2 { margin-top: 0; color: #444; }
        table { width: 100%; border-collapse: collapse; }
        th, td { padding: 10px; text-align: left; border-bottom: 1px solid #eee; }
        th { background: #f9f9f9; }
        .budget-ok { color: #27ae60; font-weight: bold; }
        .budget-warn { color: #f39c12; font-weight: bold; }
        .budget-exceeded { color: #c0392b; font-weight: bold; }
        .total { font-size: 1.2em; font-weight: bold; color: #2980b9; }
        .footer { color: #999; font-size: 12px; margin-top: 30px; }
    </style>
</head>
<body>
    <h1>🏛️ Athanor — Cost Dashboard</h1>
    <p>Generated: {{ generated_at }}</p>

    <div class="card">
        <h2>Total This Week</h2>
        <p class="total">{{ total_weekly_cost }} €</p>
        <p>{{ total_weekly_requests }} requests across {{ user_count }} user(s)</p>
    </div>

    {% for user_email, data in users.items() %}
    <div class="card">
        <h2>{{ user_email }}</h2>
        <table>
            <tr>
                <th>Period</th>
                <th>Spent (€)</th>
                <th>Requests</th>
                <th>Status</th>
            </tr>
            <tr>
                <td>This week</td>
                <td>{{ data.week.spent_eur | round(2) }} €</td>
                <td>{{ data.week.requests }}</td>
                <td class="{{ data.week.status_class }}">{{ data.week.status }}</td>
            </tr>
            <tr>
                <td>Today</td>
                <td>{{ data.day.spent_eur | round(2) }} €</td>
                <td>{{ data.day.requests }}</td>
                <td class="{{ data.day.status_class }}">{{ data.day.status }}</td>
            </tr>
        </table>
    </div>
    {% endfor %}

    {% if not users %}
    <div class="card">
        <p>No budget data available yet. Make sure the Budget Tracker filter is enabled in OpenWebUI.</p>
    </div>
    {% endif %}

    <p class="footer">Athanor Cost Dashboard — Scale-to-zero on Cloud Run</p>
</body>
</html>
"""


def get_budget_status(spent: float, budget: float) -> tuple[str, str]:
    """Return status text and CSS class."""
    if budget <= 0:
        return "No budget set", "budget-warn"
    pct = (spent / budget) * 100
    if pct >= 100:
        return f"Exceeded ({pct:.0f}%)", "budget-exceeded"
    elif pct >= 75:
        return f"Warning ({pct:.0f}%)", "budget-warn"
    else:
        return f"OK ({pct:.0f}%)", "budget-ok"


@app.route("/")
def dashboard():
    """Serve the cost dashboard."""
    now = datetime.now(timezone.utc)
    week_key = f"week_{now.isocalendar()[0]}_w{now.isocalendar()[1]:02d}"
    day_key = now.strftime("day_%Y-%m-%d")

    users_data = {}
    total_cost = 0.0
    total_requests = 0

    try:
        client = storage.Client()
        bucket = client.bucket(GCS_BUCKET)
        blob = bucket.blob("budget_usage.json")
        if blob.exists():
            usage = json.loads(blob.download_as_text())

            for user_email, user_data in usage.items():
                week_data = user_data.get(week_key, {"spent_eur": 0.0, "requests": 0})
                day_data = user_data.get(day_key, {"spent_eur": 0.0, "requests": 0})

                # Default budgets (€2/week, €0.50/day)
                week_status, week_class = get_budget_status(week_data.get("spent_eur", 0), 2.0)
                day_status, day_class = get_budget_status(day_data.get("spent_eur", 0), 0.50)

                users_data[user_email] = {
                    "week": {
                        "spent_eur": week_data.get("spent_eur", 0),
                        "requests": week_data.get("requests", 0),
                        "status": week_status,
                        "status_class": week_class,
                    },
                    "day": {
                        "spent_eur": day_data.get("spent_eur", 0),
                        "requests": day_data.get("requests", 0),
                        "status": day_status,
                        "status_class": day_class,
                    },
                }

                total_cost += week_data.get("spent_eur", 0)
                total_requests += week_data.get("requests", 0)
    except Exception as e:
        app.logger.error("Failed to load budget data: %s", e)

    return render_template_string(
        DASHBOARD_TEMPLATE,
        generated_at=now.strftime("%Y-%m-%d %H:%M UTC"),
        users=users_data,
        total_weekly_cost=round(total_cost, 2),
        total_weekly_requests=total_requests,
        user_count=len(users_data),
    )


@app.route("/health")
def health():
    return {"status": "ok"}, 200


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 8080)))
