"""Budget Tracker — OpenWebUI Filter Function.

Tracks per-user estimated cost (tokens × model price) with automatic
price refresh from OpenRouter API. Blocks requests when weekly or daily
budget is exceeded.

Install: upload via OpenWebUI Admin > Functions, then enable as a global filter.
Configure: set Valves in the admin UI (budgets, user overrides, etc.).
"""

import json
import logging
import time
from datetime import datetime, timezone, timedelta
from typing import Optional

import httpx
from pydantic import BaseModel, Field

logger = logging.getLogger("athanor.budget_tracker")

# EUR/USD rate — refreshed periodically from a free API
DEFAULT_EUR_USD_RATE = 0.92  # fallback

# OpenRouter pricing API
OPENROUTER_MODELS_URL = "https://openrouter.ai/api/v1/models"

# VertexAI → OpenRouter model mapping for price estimation
# When a VertexAI model is used, we map it to an equivalent OpenRouter model
# for cost estimation. This avoids maintaining a static VertexAI price table.
VERTEXAI_TO_OPENROUTER_MAP = {
    # Gemini models
    "gemini-2.5-flash-lite": "openrouter/google/gemini-2.0-flash-lite",
    "gemini-2.5-flash": "openrouter/google/gemini-2.0-flash",
    "gemini-2.5-pro": "openrouter/google/gemini-2.0-pro",
    "gemini-2.0-flash-lite": "openrouter/google/gemini-2.0-flash-lite",
    "gemini-2.0-flash": "openrouter/google/gemini-2.0-flash",
    "gemini-2.0-pro": "openrouter/google/gemini-2.0-pro",
    "gemini-1.5-flash": "openrouter/google/gemini-1.5-flash",
    "gemini-1.5-pro": "openrouter/google/gemini-1.5-pro",
    # Generic fallbacks
    "gemini": "openrouter/google/gemini-2.0-flash",
    "vertexai": "openrouter/google/gemini-2.0-flash",
}


class Filter:
    """Per-user budget tracking filter for OpenWebUI.

    OpenWebUI expects a class named "Function" with inlet/outlet methods.
    """

    class Valves(BaseModel):
        # Global budgets (EUR)
        default_weekly_budget_eur: float = Field(
            default=2.0,
            description="Default weekly budget per user (EUR)",
        )
        default_daily_budget_eur: float = Field(
            default=0.50,
            description="Default daily budget per user (EUR)",
        )

        # Per-user overrides: JSON {"email": {"weekly": 5.0, "daily": 1.0}}
        user_budgets_json: str = Field(
            default="{}",
            description='Per-user budget overrides as JSON: {"email": {"weekly": 5.0, "daily": 1.0}}',
        )

        # OpenRouter API key for fetching model prices
        openrouter_api_key: str = Field(
            default="",
            description="OpenRouter API key (for fetching model prices)",
        )

        # VertexAI proxy API key (for tracking VertexAI usage)
        vertexai_proxy_api_key: str = Field(
            default="",
            description="VertexAI proxy API key",
        )

        # Block or just warn when budget exceeded
        block_on_exceeded: bool = Field(
            default=True,
            description="Block requests when budget is exceeded (or just warn)",
        )

        # Price refresh interval (hours)
        price_refresh_hours: int = Field(
            default=24,
            description="How often to refresh OpenRouter model prices (hours)",
        )

        enabled: bool = Field(default=True)

    def __init__(self):
        self.valves = self.Valves()
        self._model_prices: dict[str, dict] = {}
        self._last_price_refresh: float = 0
        self._eur_usd_rate: float = DEFAULT_EUR_USD_RATE
        self._usage_path = "/app/backend/data/budget_usage.json"
        self._usage: dict = {}
        self._load_usage()

    def _load_usage(self) -> None:
        """Load budget usage from disk."""
        try:
            import os
            from pathlib import Path
            p = Path(self._usage_path)
            if p.exists():
                self._usage = json.loads(p.read_text())
        except (json.JSONDecodeError, OSError) as e:
            logger.warning("Could not load budget usage: %s", e)
            self._usage = {}

    def _save_usage(self) -> None:
        """Persist budget usage to disk."""
        try:
            from pathlib import Path
            p = Path(self._usage_path)
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text(json.dumps(self._usage, indent=2))
        except OSError as e:
            logger.warning("Could not save budget usage: %s", e)

    def _get_user_key(self, user_email: str) -> str:
        return user_email.lower().strip()

    def _get_user_budgets(self, user_email: str) -> dict:
        """Get weekly and daily budget for a user."""
        overrides = {}
        try:
            overrides = json.loads(self.valves.user_budgets_json)
        except (json.JSONDecodeError, TypeError):
            pass

        user_key = self._get_user_key(user_email)
        user_override = overrides.get(user_key, {})

        return {
            "weekly": user_override.get("weekly", self.valves.default_weekly_budget_eur),
            "daily": user_override.get("daily", self.valves.default_daily_budget_eur),
        }

    def _get_week_start(self) -> str:
        """Get ISO week key for current week."""
        now = datetime.now(timezone.utc)
        return f"week_{now.isocalendar()[0]}_w{now.isocalendar()[1]:02d}"

    def _get_day_key(self) -> str:
        """Get day key for current day."""
        return datetime.now(timezone.utc).strftime("day_%Y-%m-%d")

    def _get_user_spent(self, user_email: str) -> dict:
        """Get current week and day spending for a user."""
        user_key = self._get_user_key(user_email)
        week_key = self._get_week_start()
        day_key = self._get_day_key()

        user_data = self._usage.get(user_key, {})
        week_data = user_data.get(week_key, {"spent_eur": 0.0, "requests": 0})
        day_data = user_data.get(day_key, {"spent_eur": 0.0, "requests": 0})

        return {
            "week": week_data,
            "day": day_data,
        }

    def _record_usage(self, user_email: str, cost_eur: float) -> None:
        """Record usage for a user."""
        user_key = self._get_user_key(user_email)
        week_key = self._get_week_start()
        day_key = self._get_day_key()

        if user_key not in self._usage:
            self._usage[user_key] = {}

        for key in [week_key, day_key]:
            if key not in self._usage[user_key]:
                self._usage[user_key][key] = {"spent_eur": 0.0, "requests": 0}
            self._usage[user_key][key]["spent_eur"] += cost_eur
            self._usage[user_key][key]["requests"] += 1

        # Cleanup old data (keep last 8 weeks + 7 days)
        self._cleanup_old_data()
        self._save_usage()

    def _cleanup_old_data(self) -> None:
        """Remove data older than 8 weeks to prevent unbounded growth."""
        now = datetime.now(timezone.utc)
        cutoff_week = now - timedelta(weeks=8)
        cutoff_day = now - timedelta(days=7)

        for user_key in list(self._usage.keys()):
            user_data = self._usage[user_key]
            for key in list(user_data.keys()):
                if key.startswith("week_"):
                    try:
                        year = int(key.split("_")[1])
                        week = int(key.split("w")[1])
                        # Approximate: if year < cutoff year or (year == cutoff year and week < cutoff week)
                        cutoff_iso = cutoff_week.isocalendar()
                        if year < cutoff_iso[0] or (year == cutoff_iso[0] and week < cutoff_iso[1] - 8):
                            del user_data[key]
                    except (ValueError, IndexError):
                        del user_data[key]
                elif key.startswith("day_"):
                    try:
                        day_date = datetime.strptime(key, "day_%Y-%m-%d").replace(tzinfo=timezone.utc)
                        if day_date < cutoff_day:
                            del user_data[key]
                    except ValueError:
                        del user_data[key]

            # Remove user if no data left
            if not user_data:
                del self._usage[user_key]

    async def _refresh_prices(self) -> None:
        """Fetch model prices from OpenRouter API."""
        now = time.time()
        if now - self._last_price_refresh < self.valves.price_refresh_hours * 3600:
            return  # Not yet time to refresh

        if not self.valves.openrouter_api_key:
            logger.warning("OpenRouter API key not set — cannot refresh prices")
            return

        try:
            async with httpx.AsyncClient(timeout=30) as client:
                resp = await client.get(
                    OPENROUTER_MODELS_URL,
                    headers={"Authorization": f"Bearer {self.valves.openrouter_api_key}"},
                )
                resp.raise_for_status()
                data = resp.json()

                for model in data.get("data", []):
                    model_id = model.get("id", "")
                    pricing = model.get("pricing", {})
                    # OpenRouter returns USD per token
                    input_usd = float(pricing.get("prompt", 0))
                    output_usd = float(pricing.get("completion", 0))

                    # Convert to EUR per 1M tokens
                    self._model_prices[model_id] = {
                        "input_per_1m": round(input_usd * self._eur_usd_rate * 1_000_000, 4),
                        "output_per_1m": round(output_usd * self._eur_usd_rate * 1_000_000, 4),
                    }

                self._last_price_refresh = now
                logger.info("Refreshed prices for %d models", len(self._model_prices))
        except Exception as e:
            logger.error("Failed to refresh prices: %s", e)

    def _estimate_cost(self, model_id: str, input_tokens: int, output_tokens: int) -> float:
        """Estimate cost in EUR for a request."""
        # Try OpenRouter prices first
        if model_id in self._model_prices:
            prices = self._model_prices[model_id]
            input_cost = (input_tokens / 1_000_000) * prices["input_per_1m"]
            output_cost = (output_tokens / 1_000_000) * prices["output_per_1m"]
            return round(input_cost + output_cost, 6)

        # Fallback: try VertexAI → OpenRouter mapping
        for vertex_prefix, openrouter_model in VERTEXAI_TO_OPENROUTER_MAP.items():
            if vertex_prefix in model_id.lower():
                if openrouter_model in self._model_prices:
                    prices = self._model_prices[openrouter_model]
                    input_cost = (input_tokens / 1_000_000) * prices["input_per_1m"]
                    output_cost = (output_tokens / 1_000_000) * prices["output_per_1m"]
                    logger.debug(
                        "VertexAI model %s mapped to %s for pricing",
                        model_id,
                        openrouter_model,
                    )
                    return round(input_cost + output_cost, 6)
                else:
                    # If mapped model not in prices, fall through to default
                    logger.warning(
                        "Mapped OpenRouter model %s not in price list for VertexAI model %s",
                        openrouter_model,
                        model_id,
                    )
                    break

        # Default fallback: assume Gemini Flash pricing (€0.15/1M input, €0.60/1M output)
        logger.warning("Unknown model %s — using default pricing", model_id)
        input_cost = (input_tokens / 1_000_000) * 0.15  # Gemini Flash input
        output_cost = (output_tokens / 1_000_000) * 0.60  # Gemini Flash output
        return round(input_cost + output_cost, 6)

    def _check_budget(self, user_email: str, estimated_cost: float) -> dict:
        """Check if user has budget remaining. Returns status dict."""
        budgets = self._get_user_budgets(user_email)
        spent = self._get_user_spent(user_email)

        week_remaining = budgets["weekly"] - spent["week"]["spent_eur"]
        day_remaining = budgets["daily"] - spent["day"]["spent_eur"]

        exceeded = {
            "weekly": week_remaining <= 0,
            "daily": day_remaining <= 0,
        }

        return {
            "budgets": budgets,
            "spent": spent,
            "remaining": {
                "weekly": round(max(0, week_remaining), 4),
                "daily": round(max(0, day_remaining), 4),
            },
            "exceeded": exceeded,
            "estimated_cost": round(estimated_cost, 4),
        }

    def _build_budget_message(self, status: dict) -> str:
        """Build a user-friendly budget status message."""
        spent_week = status["spent"]["week"]["spent_eur"]
        spent_day = status["spent"]["day"]["spent_eur"]
        remaining_week = status["remaining"]["weekly"]
        remaining_day = status["remaining"]["daily"]
        budget_week = status["budgets"]["weekly"]
        budget_day = status["budgets"]["daily"]

        return (
            f"⚠️ Budget used: {spent_week:.2f}€/{budget_week:.2f}€ this week "
            f"({remaining_week:.2f}€ remaining) | "
            f"{spent_day:.2f}€/{budget_day:.2f}€ today "
            f"({remaining_day:.2f}€ remaining)"
        )

    async def inlet(self, body: dict, __user__: Optional[dict] = None) -> dict:
        """Check budget before sending request."""
        if not self.valves.enabled or not __user__:
            return body

        user_email = __user__.get("email", "")
        if not user_email:
            return body

        # Refresh prices asynchronously
        await self._refresh_prices()

        # Estimate cost based on model and token count from the request
        model = body.get("model", "")
        messages = body.get("messages", [])
        input_tokens = sum(len(m.get("content", "")) for m in messages) // 4  # rough estimate: 4 chars/token

        # We can't know output tokens yet, estimate 200 tokens
        estimated_cost = self._estimate_cost(model, input_tokens, 200)

        # Check budget
        status = self._check_budget(user_email, estimated_cost)

        if status["exceeded"]["daily"] or status["exceeded"]["weekly"]:
            exceeded_type = "daily" if status["exceeded"]["daily"] else "weekly"
            msg = (
                f"🚫 {exceeded_type.capitalize()} budget exceeded. "
                f"{self._build_budget_message(status)}"
            )
            if self.valves.block_on_exceeded:
                # Return an error response instead of forwarding
                return {
                    "error": {
                        "message": msg,
                        "type": "budget_exceeded",
                        "code": 429,
                    }
                }
            else:
                # Add warning to system prompt
                system_msg = {"role": "system", "content": msg}
                body.setdefault("messages", []).insert(0, system_msg)

        return body

    def outlet(self, body: dict, __user__: Optional[dict] = None) -> dict:
        """Record actual usage from the response."""
        if not self.valves.enabled or not __user__:
            return body

        user_email = __user__.get("email", "")
        if not user_email:
            return body

        # Extract usage from response metadata if available
        usage = body.get("usage", {})
        input_tokens = usage.get("prompt_tokens", 0)
        output_tokens = usage.get("completion_tokens", 0)

        if input_tokens or output_tokens:
            model = body.get("model", "")
            cost = self._estimate_cost(model, input_tokens, output_tokens)
            self._record_usage(user_email, cost)

        return body
