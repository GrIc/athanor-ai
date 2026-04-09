import logging
from typing import Optional

from lib.rag_core.client import ResilientClient
from lib.rag_core.embeddings import EmbeddingClient
from lib.rag_core.store import VectorStore
from lib.agents.template import render_system_prompt

logger = logging.getLogger(__name__)

class BaseAgent:
    """
    Base conversational agent with:
    - System prompt loaded from agents/defs/default.md via render_system_prompt
    - Checkpoint context injection
    - User hint injection
    - RAG retrieval
    """
    def __init__(self, project_name: str, store: "VectorStore",
                 client: "ResilientClient", embed_client: "EmbeddingClient",
                 checkpoint: str | None = None,
                 system_prompt_hint: str | None = None,
                 chat_model: str = "gemini-2.5-flash"):
        self.project_name = project_name
        self.store = store
        self.client = client
        self.embed_client = embed_client
        self.checkpoint = checkpoint
        self.chat_model = chat_model
        self.system_prompt = render_system_prompt(project_name, checkpoint, system_prompt_hint)

    def answer(self, user_message: str, history: list[dict] | None = None) -> str:
        """
        1. Embed user_message
        2. Search store → top 5 chunks
        3. Build messages: system_prompt + RAG context + history + user_message
        4. Call client.chat()
        """
        # 1. Embed user_message
        query_embedding = self.embed_client.embed_batch([user_message])[0]

        # 2. Search store → top 5 chunks
        results = self.store.search(query_embedding, top_k=5)

        rag_context = ""
        if results:
            context_parts = []
            for i, r in enumerate(results, 1):
                source = r.get("source", "unknown")
                text = r.get("text", "")
                context_parts.append(f"--- Document {i} ({source}) ---\n{text}\n")
            rag_context = "## Context documents\n" + "\n".join(context_parts)

        # 3. Build messages
        messages = [
            {"role": "system", "content": self.system_prompt}
        ]

        if rag_context:
             messages.append({"role": "system", "content": rag_context})

        if history:
            messages.extend(history)

        messages.append({"role": "user", "content": user_message})

        # 4. Call client.chat()
        return self.client.chat(messages=messages, model=self.chat_model)