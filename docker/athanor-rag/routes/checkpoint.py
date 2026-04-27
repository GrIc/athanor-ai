from fastapi import APIRouter, HTTPException, Depends
from typing import Optional

router = APIRouter()

@router.get("/api/projects/{name}/checkpoint")
async def get_checkpoint(name: str, token: str = Depends(lambda x: x)):
    """Get checkpoint content from GCS."""
    from ..main import manifest
    from google.cloud import storage
    import os

    if name not in manifest:
        raise HTTPException(status_code=404, detail=f"Project '{name}' not found")

    RAG_GCS_BUCKET = os.environ.get("RAG_GCS_BUCKET", "athanor-ai-rag-data")
    client = storage.Client()
    bucket = client.bucket(RAG_GCS_BUCKET)
    blob = bucket.blob(f"checkpoints/{name}.md")

    if not blob.exists():
        return ""

    return blob.download_as_text()

@router.post("/api/projects/{name}/checkpoint")
async def post_checkpoint(name: str, checkpoint: str, token: str = Depends(lambda x: x)):
    """Write checkpoint to GCS."""
    from ..main import manifest
    from google.cloud import storage
    import os

    if name not in manifest:
        raise HTTPException(status_code=404, detail=f"Project '{name}' not found")

    RAG_GCS_BUCKET = os.environ.get("RAG_GCS_BUCKET", "athanor-ai-rag-data")
    client = storage.Client()
    bucket = client.bucket(RAG_GCS_BUCKET)
    blob = bucket.blob(f"checkpoints/{name}.md")

    blob.upload_from_string(checkpoint)

    # TODO: Also push to Proton Drive via connector (step 14)
    return {"status": "ok"}