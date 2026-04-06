"""Weekly Parental Digest — Cloud Run Job.

Downloads the OpenWebUI SQLite database from GCS, extracts conversations
from monitored child accounts for the past 7 days, summarizes them via
Gemini Flash (VertexAI), and sends an HTML email digest to the parent.
"""

import json
import logging
import os
import smtplib
import sqlite3
import tempfile
import time
from datetime import datetime, timedelta, timezone
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from pathlib import Path

import google.auth
import google.auth.transport.requests
import httpx
from google.cloud import storage
from jinja2 import Environment, FileSystemLoader

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("athanor.weekly_digest")

# Configuration from environment variables
GCS_BUCKET = os.environ["GCS_BUCKET"]
VERTEXAI_PROJECT_ID = os.environ.get("VERTEXAI_PROJECT_ID", "")
VERTEXAI_LOCATION = os.environ.get("VERTEXAI_LOCATION", "europe-west9")
MONITORED_USERS = os.environ.get("MONITORED_USERS", "").split(",")
ALERT_EMAIL = os.environ.get("ALERT_EMAIL", "")
SMTP_HOST = os.environ.get("SMTP_HOST", "smtp.gmail.com")
SMTP_PORT = int(os.environ.get("SMTP_PORT", "587"))
SMTP_USER = os.environ.get("SMTP_USER", "")
SMTP_PASSWORD = os.environ.get("SMTP_PASSWORD", "")

VERTEXAI_BASE_URL = (
    f"https://{VERTEXAI_LOCATION}-aiplatform.googleapis.com"
    f"/v1beta1/projects/{VERTEXAI_PROJECT_ID}"
    f"/locations/{VERTEXAI_LOCATION}/endpoints/openapi"
)


def download_db(tmp_dir: str) -> str:
    """Download the OpenWebUI SQLite database from GCS."""
    client = storage.Client()
    bucket = client.bucket(GCS_BUCKET)
    db_path = os.path.join(tmp_dir, "webui.db")
    bucket.blob("webui.db").download_to_filename(db_path)
    return db_path


def get_user_conversations(
    db_path: str, user_email: str, since: datetime
) -> list[dict]:
    """Query conversations for a user from the past week."""
    conn = sqlite3.connect(db_path, check_same_thread=False)
    conn.row_factory = sqlite3.Row

    # OpenWebUI stores chats with user_id referencing the user table.
    # The chat column contains a JSON blob with the full conversation.
    rows = conn.execute(
        """
        SELECT c.id, c.title, c.chat, c.created_at, c.updated_at
        FROM chat c
        JOIN user u ON c.user_id = u.id
        WHERE LOWER(u.email) = LOWER(?)
          AND c.updated_at >= ?
        ORDER BY c.updated_at DESC
        """,
        (user_email.strip(), since.timestamp()),
    ).fetchall()

    conversations = []
    for row in rows:
        chat_data = json.loads(row["chat"]) if row["chat"] else {}
        messages = chat_data.get("messages", [])
        conversations.append({
            "id": row["id"],
            "title": row["title"] or "Sans titre",
            "date": datetime.fromtimestamp(
                row["updated_at"], tz=timezone.utc
            ).strftime("%d/%m"),
            "message_count": len(messages),
            "messages": messages,
        })

    conn.close()
    return conversations


def get_user_name(db_path: str, user_email: str) -> str:
    """Get the display name for a user email."""
    conn = sqlite3.connect(db_path, check_same_thread=False)
    row = conn.execute(
        "SELECT name FROM user WHERE LOWER(email) = LOWER(?)",
        (user_email.strip(),),
    ).fetchone()
    conn.close()
    return row[0] if row else user_email


def get_weekly_alerts(since: datetime, user_email: str) -> list[dict]:
    """Read alerts from the parental_alerts.json log file on GCS."""
    try:
        client = storage.Client()
        bucket = client.bucket(GCS_BUCKET)
        blob = bucket.blob("parental_alerts.json")
        if not blob.exists():
            return []
        alerts = json.loads(blob.download_as_text())
        return [
            a
            for a in alerts
            if a.get("user", "").lower() == user_email.strip().lower()
            and datetime.fromisoformat(a["timestamp"]) >= since
        ]
    except Exception:
        return []


def summarize_conversations(conversations: list[dict], access_token: str) -> str:
    """Summarize a week of conversations using Gemini Flash via VertexAI."""
    if not conversations or not VERTEXAI_PROJECT_ID:
        return ""

    # Build a condensed view of the conversations for the LLM
    conv_summaries = []
    for conv in conversations[:20]:  # Limit to 20 conversations
        messages = conv["messages"]
        # Take first and last few messages for context
        sample = messages[:3] + (messages[-2:] if len(messages) > 5 else [])
        texts = [
            f"{m.get('role', '?')}: {m.get('content', '')[:200]}" for m in sample
        ]
        conv_summaries.append(
            f"--- {conv['title']} ({conv['message_count']} messages) ---\n"
            + "\n".join(texts)
        )

    prompt = (
        "Tu es un assistant de monitoring parental. Voici les conversations "
        "d'un adolescent avec une IA cette semaine. Fais un resume en 3-5 phrases "
        "des principaux sujets abordes, du ton general, et signale tout sujet "
        "potentiellement preoccupant (sans dramatiser). Reponds en francais.\n\n"
        + "\n\n".join(conv_summaries)
    )

    try:
        resp = httpx.post(
            f"{VERTEXAI_BASE_URL}/chat/completions",
            json={
                "model": "gemini-2.5-flash-lite",
                "messages": [{"role": "user", "content": prompt}],
                "max_tokens": 500,
            },
            headers={
                "Authorization": f"Bearer {access_token}",
                "Content-Type": "application/json",
            },
            timeout=60.0,
        )
        resp.raise_for_status()
        return resp.json()["choices"][0]["message"]["content"]
    except Exception as e:
        return f"(Resume indisponible: {e})"


def send_email(html_content: str, max_retries: int = 3) -> None:
    """Send the digest email via SMTP with retry logic."""
    if not all([SMTP_USER, SMTP_PASSWORD, ALERT_EMAIL]):
        logger.error("SMTP credentials or alert email not configured — skipping digest")
        return

    msg = MIMEMultipart("alternative")
    msg["Subject"] = (
        f"[Athanor] Digest Hebdo — {datetime.now(timezone.utc).strftime('%d/%m/%Y')}"
    )
    msg["From"] = SMTP_USER
    msg["To"] = ALERT_EMAIL
    msg.attach(MIMEText(html_content, "html", "utf-8"))

    last_error = None
    for attempt in range(1, max_retries + 1):
        try:
            logger.info("Sending digest email (attempt %d/%d)...", attempt, max_retries)
            with smtplib.SMTP(SMTP_HOST, SMTP_PORT, timeout=30) as server:
                server.starttls()
                server.login(SMTP_USER, SMTP_PASSWORD)
                server.send_message(msg)
            logger.info("Digest email sent successfully to %s", ALERT_EMAIL)
            return
        except smtplib.SMTPException as e:
            last_error = e
            logger.warning("SMTP error on attempt %d: %s", attempt, e)
        except OSError as e:
            last_error = e
            logger.warning("Network error on attempt %d: %s", attempt, e)

        if attempt < max_retries:
            time.sleep(2 ** attempt)  # Exponential backoff: 2s, 4s, 8s

    logger.error("Failed to send digest after %d attempts: %s", max_retries, last_error)
    raise RuntimeError(f"Failed to send digest email: {last_error}")


def main() -> None:
    now = datetime.now(timezone.utc)
    since = now - timedelta(days=7)
    week_start = since.strftime("%d/%m/%Y")
    week_end = now.strftime("%d/%m/%Y")

    # Get Google access token for VertexAI calls
    credentials, _ = google.auth.default(
        scopes=["https://www.googleapis.com/auth/cloud-platform"]
    )
    credentials.refresh(google.auth.transport.requests.Request())
    access_token = credentials.token

    with tempfile.TemporaryDirectory() as tmp_dir:
        logger.info("Downloading database from gs://%s/webui.db...", GCS_BUCKET)
        db_path = download_db(tmp_dir)

        users_data = []
        for email in MONITORED_USERS:
            email = email.strip()
            if not email:
                continue

            logger.info("Processing user: %s", email)
            name = get_user_name(db_path, email)
            conversations = get_user_conversations(db_path, email, since)
            alerts = get_weekly_alerts(since, email)
            summary = summarize_conversations(conversations, access_token)

            users_data.append({
                "name": name,
                "email": email,
                "conversation_count": len(conversations),
                "conversations": [
                    {
                        "date": c["date"],
                        "title": c["title"],
                        "message_count": c["message_count"],
                    }
                    for c in conversations
                ],
                "summary": summary,
                "alerts": alerts,
            })

        # Render HTML email (inside the with block — db still available if needed)
        templates_dir = Path(__file__).parent / "templates"
        env = Environment(loader=FileSystemLoader(str(templates_dir)), autoescape=True)
        template = env.get_template("digest_email.html")
        html = template.render(users=users_data, week_start=week_start, week_end=week_end)

        # Send email
        logger.info("Sending digest to %s...", ALERT_EMAIL)
        send_email(html)


if __name__ == "__main__":
    main()
