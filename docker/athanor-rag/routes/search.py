from fastapi import APIRouter, HTTPException, Depends
from typing import Dict, Any, List
from pydantic import BaseModel

router = APIRouter()

class SearchRequest(BaseModel):
    query: str
    top_k: int = 8

class SearchResult(BaseModel):
    text: str
    source: str
    score: float

@router.post("/api/projects/{name}/search")
async def search_project(name: str, request: SearchRequest, token: str = Depends(lambda x: x)):
    """Search within a project's vector store."""
    from ..main import stores

    if name not in stores:
        raise HTTPException(status_code=404, detail=f"Project '{name}' not found")

    store = stores[name]

    # Import here to avoid circular imports
    from lib.rag_core.embeddings import EmbeddingClient
    from lib.rag_core.client import ResilientClient
    import os

    # We need to get the embedding client - this is a bit tricky without DI
    # For now, we'll create a new one (in production this should be shared)
    # This is a limitation of this simplified approach
    gemini_client = ResilientClient(
        api_key=os.environ.get("VERTEXAI_PROXY_KEY", ""),
        base_url=os.environ.get("VERTEXAI_PROXY_URL", "")
    )
    embed_client = EmbeddingClient(gemini_client, model=os.environ.get("EMBED_MODEL", "text-multilingual-embedding-002"))

    # Embed the query
    query_embedding = embed_client.embed_batch([request.query])[0]

    # Search
    results = store.search(query_embedding, top_k=request.top_k)

    # Format results
    formatted_results = []
    for r in results:
        formatted_results.append(SearchResult(
            text=r.get("text", ""),
            source=r.get("source", "unknown"),
            score=r.get("score", 0.0)
        ))

    return {"results": [r.dict() for r in formatted_results]}