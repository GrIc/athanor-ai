"""Parental Monitor — OpenWebUI Filter Function.

Monitors conversations from specified child accounts and sends email
alerts when concerning keywords are detected. Does NOT block messages.

Install: upload via OpenWebUI Admin > Functions, then enable as a global filter.
Configure: set Valves in the admin UI (monitored emails, SMTP credentials, etc.).
"""

import json
import logging
import re
import smtplib
import time
from datetime import datetime, timezone
from email.mime.text import MIMEText
from pathlib import Path
from typing import Optional

from pydantic import BaseModel, Field

logger = logging.getLogger("athanor.parental_monitor")


# Concerning keyword categories — each maps to a list of regex patterns.
# Patterns are case-insensitive and match whole words where possible.
DEFAULT_KEYWORDS = {
    "self_harm": [
        r"\bsuicid\w*\b",
        r"\bse couper\b",
        r"\bme tuer\b",
        r"\benvie de mourir\b",
        r"\bautomutilation\b",
        r"\bself.?harm\b",
        r"\bme faire du mal\b",
    ],
    "violence": [
        r"\btuer quelqu\w*\b",
        r"\bfaire du mal\b",
        r"\barme\s?\w*\b",
        r"\bfrapper\b",
        r"\bagresser\b",
        r"\bmenacer\b",
    ],
    "drugs": [
        r"\bdrogue\w*\b",
        r"\bcocaine\b",
        r"\bhero[iy]ne\b",
        r"\becstasy\b",
        r"\bmdma\b",
        r"\blsd\b",
        r"\bfumer\s+du\b",
        r"\bdealer\b",
    ],
    "sexual_predation": [
        r"\benvoie.{0,10}photo\b",
        r"\bwebcam\b",
        r"\bnude\w*\b",
        r"\brencontrer\s+en\s+secret\b",
        r"\bne dis pas\s+[aà]\s+tes\s+parents\b",
    ],
    "cyberbullying": [
        r"\bva mourir\b",
        r"\bpersonne ne t.aime\b",
        r"\binutile\b",
        r"\bhar[cç]el\w*\b",
    ],
    "runaway": [
        r"\bfugue\w*\b",
        r"\bme sauver\b",
        r"\bpartir de chez moi\b",
        r"\bne plus rentrer\b",
        r"\bje m.enfuis\b",
        r"\brun away\b",
    ],
    "radicalization": [
        r"\bjihad\b",
        r"\bdaech\b",
        r"\bétat islamique\b",
        r"\bisis\b",
        r"\bpasser à l.acte\b",
        r"\battentat\b",
    ],
}


class Filter:
    """Parental monitoring filter for OpenWebUI."""

    class Valves(BaseModel):
        monitored_emails: str = Field(
            default="",
            description="Comma-separated email addresses of monitored child accounts",
        )
        alert_email: str = Field(
            default="",
            description="Parent email address to receive alerts",
        )
        smtp_host: str = Field(default="smtp.gmail.com")
        smtp_port: int = Field(default=587)
        smtp_user: str = Field(
            default="",
            description="Gmail address for sending alerts",
        )
        smtp_password: str = Field(
            default="",
            description="Gmail App Password (not your main password)",
        )
        extra_keywords_json: str = Field(
            default="{}",
            description=(
                'Additional keywords as JSON: {"category": ["pattern1", "pattern2"]}'
            ),
        )
        cooldown_seconds: int = Field(
            default=300,
            description="Minimum seconds between alerts for the same category+user",
        )
        enabled: bool = Field(default=True)

    def __init__(self):
        self.valves = self.Valves()
        self._compiled_patterns: dict[str, list[re.Pattern]] = {}
        self._last_alerts: dict[str, float] = {}
        self._log_path = Path("/app/backend/data/parental_alerts.json")
        self._rate_limit_path = Path("/app/backend/data/parental_rate_limits.json")
        self._load_rate_limits()
        self._compile_patterns()

    def _load_rate_limits(self) -> None:
        """Load rate limit state from disk (survives container restarts)."""
        try:
            if self._rate_limit_path.exists():
                self._last_alerts = json.loads(self._rate_limit_path.read_text())
        except (json.JSONDecodeError, OSError) as e:
            logger.warning("Could not load rate limits: %s", e)
            self._last_alerts = {}

    def _save_rate_limits(self) -> None:
        """Persist rate limit state to disk."""
        try:
            self._rate_limit_path.parent.mkdir(parents=True, exist_ok=True)
            self._rate_limit_path.write_text(json.dumps(self._last_alerts))
        except OSError as e:
            logger.warning("Could not save rate limits: %s", e)

    def _compile_patterns(self) -> None:
        """Compile keyword patterns for fast matching."""
        keywords = dict(DEFAULT_KEYWORDS)
        try:
            extra = json.loads(self.valves.extra_keywords_json)
            if isinstance(extra, dict):
                for cat, patterns in extra.items():
                    keywords.setdefault(cat, []).extend(patterns)
        except (json.JSONDecodeError, TypeError):
            pass

        self._compiled_patterns = {
            cat: [re.compile(p, re.IGNORECASE) for p in patterns]
            for cat, patterns in keywords.items()
        }

    def _get_monitored_emails(self) -> set[str]:
        return {
            e.strip().lower()
            for e in self.valves.monitored_emails.split(",")
            if e.strip()
        }

    def _check_content(self, text: str) -> list[tuple[str, str]]:
        """Check text against keyword patterns. Returns list of (category, matched_text)."""
        matches = []
        for category, patterns in self._compiled_patterns.items():
            for pattern in patterns:
                match = pattern.search(text)
                if match:
                    matches.append((category, match.group()))
                    break  # One match per category is enough
        return matches

    def _should_alert(self, user_email: str, category: str) -> bool:
        """Rate-limit alerts: one per category+user per cooldown period."""
        key = f"{user_email}:{category}"
        now = time.time()
        last = self._last_alerts.get(key, 0)
        if now - last < self.valves.cooldown_seconds:
            return False
        self._last_alerts[key] = now
        self._save_rate_limits()
        return True

    def _send_alert(
        self,
        user_email: str,
        user_name: str,
        matches: list[tuple[str, str]],
        message_text: str,
        direction: str,
    ) -> None:
        """Send an alert email to the parent."""
        if not all(
            [
                self.valves.alert_email,
                self.valves.smtp_user,
                self.valves.smtp_password,
            ]
        ):
            logger.warning("SMTP not configured — skipping alert for %s", user_email)
            return

        categories = ", ".join(cat for cat, _ in matches)
        matched_words = ", ".join(f'"{word}"' for _, word in matches)
        timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")

        # Truncate message for the alert (don't send full conversation)
        preview = message_text[:500] + ("..." if len(message_text) > 500 else "")

        subject = f"[Athanor] Alert: {categories} - {user_name}"
        body = (
            f"Parental Monitor Alert\n"
            f"{'=' * 40}\n\n"
            f"User: {user_name} ({user_email})\n"
            f"Time: {timestamp}\n"
            f"Direction: {direction}\n"
            f"Categories: {categories}\n"
            f"Matched: {matched_words}\n\n"
            f"Message preview:\n{preview}\n"
        )

        msg = MIMEText(body, "plain", "utf-8")
        msg["Subject"] = subject
        msg["From"] = self.valves.smtp_user
        msg["To"] = self.valves.alert_email

        try:
            with smtplib.SMTP(self.valves.smtp_host, self.valves.smtp_port) as server:
                server.starttls()
                server.login(self.valves.smtp_user, self.valves.smtp_password)
                server.send_message(msg)
            logger.info(
                "Alert email sent to %s for categories: %s", user_email, categories
            )
        except smtplib.SMTPException as e:
            logger.error("SMTP error sending alert for %s: %s", user_email, e)
        except OSError as e:
            logger.error("Network error sending alert for %s: %s", user_email, e)

    def _log_alert(
        self,
        user_email: str,
        matches: list[tuple[str, str]],
        direction: str,
    ) -> None:
        """Append alert to the JSON log file."""
        entry = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "user": user_email,
            "direction": direction,
            "categories": [cat for cat, _ in matches],
            "matched": [word for _, word in matches],
        }
        try:
            existing = []
            if self._log_path.exists():
                existing = json.loads(self._log_path.read_text())
            existing.append(entry)
            # Keep last 1000 entries
            if len(existing) > 1000:
                existing = existing[-1000:]
            self._log_path.parent.mkdir(parents=True, exist_ok=True)
            self._log_path.write_text(
                json.dumps(existing, indent=2, ensure_ascii=False)
            )
        except OSError as e:
            logger.error("Could not write alert log: %s", e)

    def _process_message(
        self,
        body: dict,
        user: Optional[dict],
        direction: str,
    ) -> dict:
        """Core monitoring logic for both inlet and outlet."""
        if not self.valves.enabled or not user:
            return body

        user_email = (user.get("email") or "").lower()
        user_name = user.get("name") or user_email

        if user_email not in self._get_monitored_emails():
            return body

        # Recompile patterns in case valves changed
        self._compile_patterns()

        # Extract message text
        messages = body.get("messages", [])
        if not messages:
            return body

        last_message = messages[-1]
        content = last_message.get("content", "")
        if not isinstance(content, str):
            return body

        matches = self._check_content(content)
        if not matches:
            return body

        # Log all matches
        self._log_alert(user_email, matches, direction)

        # Send email alerts (rate-limited per category)
        alertable = [
            (cat, word) for cat, word in matches if self._should_alert(user_email, cat)
        ]
        if alertable:
            self._send_alert(user_email, user_name, alertable, content, direction)

        return body

    def inlet(self, body: dict, __user__: Optional[dict] = None) -> dict:
        """Monitor user messages (what the child sends to the LLM)."""
        return self._process_message(body, __user__, "user_message")

    def outlet(self, body: dict, __user__: Optional[dict] = None) -> dict:
        """Monitor assistant responses (what the LLM sends back to the child)."""
        return self._process_message(body, __user__, "assistant_response")
