from fastapi import APIRouter
from typing import Dict, Any

router = APIRouter()

@router.get("/api/projects")
async def get_projects():
    """Return the manifest.json content."""
    from ..main import manifest
    return manifest