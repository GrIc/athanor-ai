import os
import json
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException, Depends, Header
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from lib.rag_core.store import VectorStore
from lib.rag_core.graph import KnowledgeGraph
from google.cloud import storage

logger = logging.getLogger(__name__)

# Security
security = HTTPBearer(auto_error=False)

# Environment variables
RAG_GCS_BUCKET = os.environ.get("RAG_GCS_BUCKET", "athanor-ai-rag-data")
VERTEXAI_PROXY_URL = os.environ.get("VERTEXAI_PROXY_URL")
VERTEXAI_PROXY_KEY = os.environ.get("VERTEXAI_PROXY_KEY")
RAG_API_KEY = os.environ.get("RAG_API_KEY", "test")  # Default for dev

# Global state (will be populated in lifespan)
stores = {}      # {project_name: VectorStore}
graphs = {}      # {project_name: KnowledgeGraph}
manifest = {}    # {project_name: dict}

def verify_token(credentials: HTTPAuthorizationCredentials = Depends(security)):
    """Verify bearer token for protected routes (except /health)"""
    if not credentials:
        raise HTTPException(status_code=401, detail="Missing authorization header")
    if credentials.credentials != RAG_API_KEY:
        raise HTTPException(status_code=401, detail="Invalid API key")
    return credentials.credentials

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Load all project snapshots from GCS at startup"""
    global stores, graphs, manifest

    logger.info("Loading project snapshots from GCS...")

    # Load manifest
    try:
        client = storage.Client()
        bucket = client.bucket(RAG_GCS_BUCKET)
        blob = bucket.blob("manifest.json")
        if blob.exists():
            manifest_content = blob.download_as_text()
            manifest = json.loads(manifest_content)
            logger.info(f"Loaded manifest with {len(manifest)} projects")
        else:
            manifest = {}
            logger.warning("No manifest found in GCS")
    except Exception as e:
        logger.error(f"Failed to load manifest: {e}")
        manifest = {}

    # Load each project's VectorStore and KnowledgeGraph
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

            logger.info(f"Loaded project {project_name}")
        except Exception as e:
            logger.error(f"Failed to load project {project_name}: {e}")
            # Create empty stores for failed projects
            stores[project_name] = VectorStore(project_name)
            graphs[project_name] = KnowledgeGraph()

    logger.info(f"Startup complete. Loaded {len(stores)} projects.")
    yield
    # Cleanup if needed
    logger.info("Shutting down...")

app = FastAPI(lifespan=lifespan)

# Import and include routers
from .routes import health, projects, search, chat, checkpoint, admin

app.include_router(health.router)
app.include_router(projects.router)
app.include_router(search.router)
app.include_router(chat.router)
app.include_router(checkpoint.router)
app.include_router(admin.router)