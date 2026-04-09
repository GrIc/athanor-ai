from fastapi import APIRouter, HTTPException, Depends
from typing import Dict, Any, List, Optional
from pydantic import BaseModel
import json
import logging

from lib.rag_core.graph import KnowledgeGraph

router = APIRouter()
logger = logging.getLogger(__name__)

class ChatMessage(BaseModel):
    role: str
    content: str

class ChatCompletionRequest(BaseModel):
    model: str  # project name
    messages: List[ChatMessage]
    stream: bool = False
    temperature: Optional[float] = None
    max_tokens: Optional[int] = None

class ChatCompletionResponseChoice(BaseModel):
    index: int
    message: ChatMessage
    finish_reason: str = "stop"

class ChatCompletionResponse(BaseModel):
    id: str = "chatcmpl-123"
    object: str = "chat.completion"
    created: int = 1717986939  # placeholder timestamp
    model: str
    choices: List[ChatCompletionResponseChoice]
    usage: Dict[str, int] = {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0}

@router.post("/v1/chat/completions")
async def chat_completions(request: ChatCompletionRequest, token: str = Depends(lambda x: x)):
    """OpenAI-compatible chat endpoint."""
    from ..main import stores, graphs, manifest

    project_name = request.model
    if project_name not in stores:
        raise HTTPException(status_code=404, detail=f"Project '{project_name}' not found")

    store = stores[project_name]
    graph = graphs.get(project_name, KnowledgeGraph())  # Default to empty if not found

    # Import LLM clients
    from lib.rag_core.client import ResilientClient
    from lib.rag_core.embeddings import EmbeddingClient
    import os

    # Initialize clients (in production, these should be shared/singletons)
    gemini_client = ResilientClient(
        api_key=os.environ.get("VERTEXAI_PROXY_KEY", ""),
        base_url=os.environ.get("VERTEXAI_PROXY_URL", "")
    )
    embed_client = EmbeddingClient(gemini_client, model=os.environ.get("EMBED_MODEL", "text-multilingual-embedding-002"))

    # Extract last user message
    user_message = ""
    for msg in reversed(request.messages):
        if msg.role == "user":
            user_message = msg.content
            break

    if not user_message:
        raise HTTPException(status_code=400, detail="No user message found")

    # 1. Embed user_message
    query_embedding = embed_client.embed_batch([user_message])[0]

    # 2. Search store → top 5 chunks
    results = store.search(query_embedding, top_k=5)

    # Build RAG context
    rag_context = ""
    if results:
        context_parts = []
        for i, r in enumerate(results, 1):
            source = r.get("source", "unknown")
            text = r.get("text", "")
            context_parts.append(f"--- Document {i} ({source}) ---\n{text}\n")
        rag_context = "## Context documents\n" + "\n".join(context_parts)

    # 3. Build messages: system_prompt + RAG context + history + user_message
    from lib.agents.template import render_system_prompt

    checkpoint = manifest.get(project_name, {}).get("checkpoint", "")
    system_prompt_hint = manifest.get(project_name, {}).get("system_prompt_hint", "")
    system_prompt = render_system_prompt(project_name, checkpoint, system_prompt_hint)

    messages = [
        {"role": "system", "content": system_prompt}
    ]

    if rag_context:
        messages.append({"role": "system", "content": rag_context})

    # Add conversation history (excluding the last user message we already have)
    history_messages = [msg for msg in request.messages if msg.role != "user" or msg.content != user_message]
    for msg in history_messages:
        messages.append({"role": msg.role, "content": msg.content})

    messages.append({"role": "user", "content": user_message})

    # 4. Call client.chat()
    try:
        response_text = gemini_client.chat(
            messages=messages,
            model=os.environ.get("CHAT_MODEL", "gemini-2.5-flash"),
            temperature=request.temperature or 0.7,
            max_tokens=request.max_tokens or 1024
        )
    except Exception as e:
        logger.error(f"LLM call failed: {e}")
        raise HTTPException(status_code=500, detail="Failed to generate response")

    # Build response
    response = ChatCompletionResponse(
        model=project_name,
        choices=[
            ChatCompletionResponseChoice(
                index=0,
                message=ChatMessage(role="assistant", content=response_text),
                finish_reason="stop"
            )
        ]
    )

    return response