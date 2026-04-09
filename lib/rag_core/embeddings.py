"""Embedding client for Athanor Phase 3 RAG."""

import os
from typing import Optional
from lib.rag_core.client import ResilientClient


class EmbeddingClient:
    """Client for obtaining embeddings from the ResilientClient."""

    def __init__(self, client: ResilientClient, model: Optional[str] = None):
        self.client = client
        self.model = model or os.getenv("EMBED_MODEL", "")
        if not self.model:
            raise ValueError(
                "No embedding model configured. Set EMBED_MODEL env var."
            )

    def embed_batch(self, texts: list[str], batch_size: int = 100) -> list[list[float]]:
        """Embed texts in batches. Returns list of embedding vectors."""
        all_embeddings = []
        for i in range(0, len(texts), batch_size):
            batch = texts[i:i + batch_size]
            embeddings = self.client.embed(batch, model=self.model)
            all_embeddings.extend(embeddings)
        return all_embeddings
