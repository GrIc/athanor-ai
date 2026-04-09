from fastapi import APIRouter
from typing import Dict, Any

router = APIRouter()

@router.get("/health")
async def health_check():
    """Health check endpoint that returns project status and chunk counts."""
    # Access global state from main.py
    from ..main import stores, graphs, manifest

    projects_info = {}
    for project_name, store in stores.items():
        chunk_count = 0
        try:
            # Get count from ChromaDB collection
            chunk_count = store.collection.count()
        except Exception:
            chunk_count = 0

        graph_nodes = 0
        try:
            graph_nodes = graphs[project_name].node_count
        except Exception:
            graph_nodes = 0

        projects_info[project_name] = {
            "chunks": chunk_count,
            "graph_nodes": graph_nodes
        }

    return {
        "status": "ok",
        "projects": projects_info
    }