from fastapi import APIRouter, HTTPException, Depends, BackgroundTasks
import os
import json
import logging

from lib.rag_core.store import VectorStore
from lib.rag_core.graph import KnowledgeGraph
from google.cloud import storage

router = APIRouter()
logger = logging.getLogger(__name__)

def get_main_state():
    # Import the main module to access global state
    from ..main import stores, graphs, manifest
    return stores, graphs, manifest

@router.post("/api/reload")
async def reload_snapshots(background_tasks: BackgroundTasks, token: str = Depends(lambda x: x)):
    """Reload all project snapshots from GCS (hot reload)."""
    stores, graphs, manifest = get_main_state()

    RAG_GCS_BUCKET = os.environ.get("RAG_GCS_BUCKET", "athanor-ai-rag-data")

    try:
        # Reload manifest
        client = storage.Client()
        bucket = client.bucket(RAG_GCS_BUCKET)
        blob = bucket.blob("manifest.json")
        if blob.exists():
            manifest_content = blob.download_as_text()
            manifest.clear()
            manifest.update(json.loads(manifest_content))
            logger.info(f"Reloaded manifest with {len(manifest)} projects")
        else:
            manifest.clear()
            logger.warning("No manifest found in GCS")

        # Reload each project
        stores.clear()
        graphs.clear()

        for project_name in manifest.keys():
            try:
                # Load VectorStore
                store = VectorStore(project_name)
                store.load_from_gcs(RAG_GCS_BUCKET, project_name)
                stores[project_name] = store

                # Load KnowledgeGraph if graph_enabled is true
                if manifest[project_name].get("graph_enabled", False):
                    graph = KnowledgeGraph()
                    graph.load_from_gcs(RAG_GCS_BUCKET, project_name)
                    graphs[project_name] = graph
                else:
                    graphs[project_name] = KnowledgeGraph()  # Empty graph

                logger.info(f"Reloaded project {project_name}")
            except Exception as e:
                logger.error(f"Failed to reload project {project_name}: {e}")
                # Create empty stores for failed projects
                stores[project_name] = VectorStore(project_name)
                graphs[project_name] = KnowledgeGraph()

        return {"status": "ok", "reloaded": len(manifest)}
    except Exception as e:
        logger.error(f"Failed to reload snapshots: {e}")
        raise HTTPException(status_code=500, detail="Failed to reload snapshots")

@router.post("/ingest/trigger")
async def trigger_ingest(background_tasks: BackgroundTasks, token: str = Depends(lambda x: x)):
    """Trigger an ingest job via Cloud Run Jobs API."""
    # This would call the Cloud Run Jobs API to start the ingest job
    # For now, we'll just return a placeholder
    # In a real implementation, you would use the Google Cloud Run Jobs client
    logger.info("Ingest trigger received (placeholder)")
    return {"status": "accepted", "message": "Ingest trigger received"}