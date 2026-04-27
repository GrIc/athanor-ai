import json
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from lib.rag_core.client import ResilientClient

EXTRACT_PROMPT = """Extract all named entities and their relations from this text. For each triplet return: {"subject": "...", "relation": "...", "object": "..."}. Return only a JSON array."""

class TripletExtractor:
    def __init__(self, client: "ResilientClient", model: str):
        self.client = client
        self.model = model  # same as chat model (e.g. gemini-2.5-flash)

    def extract_from_text(self, text: str) -> list[dict]:
        """Returns list of {subject, relation, object} dicts. Returns [] on parse error."""
        messages = [
            {"role": "system", "content": EXTRACT_PROMPT},
            {"role": "user", "content": text[:3000]},  # truncate to avoid token waste
        ]
        try:
            raw = self.client.chat(messages=messages, model=self.model,
                                   temperature=0.0, max_tokens=2048)
            # Remove Markdown block wrappers if present
            raw = raw.strip()
            if raw.startswith("```json"):
                raw = raw[7:]
            if raw.endswith("```"):
                raw = raw[:-3]

            return json.loads(raw)
        except Exception:
            return []