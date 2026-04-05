"""VertexAI Proxy — OpenAI-compatible API proxy for VertexAI Gemini models.

Receives OpenAI-compatible requests from OpenWebUI, authenticates with
Google OAuth2 via the Cloud Run service account, and forwards to VertexAI.
"""

import os

import google.auth
import google.auth.transport.requests
import httpx
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse, StreamingResponse

app = FastAPI(title="VertexAI Proxy")

VERTEXAI_PROJECT_ID = os.environ.get("VERTEXAI_PROJECT_ID", "")
VERTEXAI_LOCATION = os.environ.get("VERTEXAI_LOCATION", "europe-west9")
PROXY_API_KEY = os.environ.get("PROXY_API_KEY", "")

VERTEXAI_BASE_URL = (
    f"https://{VERTEXAI_LOCATION}-aiplatform.googleapis.com"
    f"/v1beta1/projects/{VERTEXAI_PROJECT_ID}"
    f"/locations/{VERTEXAI_LOCATION}/endpoints/openapi"
)

# Gemini models available on VertexAI in europe-west9.
# Update this list when Google adds new models to the region.
AVAILABLE_MODELS = [
    "gemini-2.5-pro",
    "gemini-2.5-flash",
    "gemini-2.0-flash",
    "gemini-2.0-flash-lite",
    "gemini-1.5-pro",
    "gemini-1.5-flash",
    "text-embedding-005",
]

# Google credentials with automatic token caching and refresh.
_credentials, _gcp_project = google.auth.default(
    scopes=["https://www.googleapis.com/auth/cloud-platform"]
)
_auth_request = google.auth.transport.requests.Request()


def _get_access_token() -> str:
    """Get a valid Google OAuth2 access token (cached, auto-refreshed)."""
    if not _credentials.valid:
        _credentials.refresh(_auth_request)
    return _credentials.token


def _extract_api_key(request: Request) -> str | None:
    """Extract API key from Authorization header (Bearer) or X-Api-Key."""
    auth_header = request.headers.get("authorization", "")
    if auth_header.lower().startswith("bearer "):
        return auth_header[7:]
    return request.headers.get("x-api-key")


def _verify_api_key(request: Request) -> None:
    if not PROXY_API_KEY:
        return
    key = _extract_api_key(request)
    if not key or key != PROXY_API_KEY:
        raise HTTPException(status_code=401, detail="Invalid API key")


def _build_models_response() -> dict:
    """Return an OpenAI-compatible /models response with available Gemini models."""
    return {
        "object": "list",
        "data": [
            {"id": m, "object": "model", "created": 0, "owned_by": "google"}
            for m in AVAILABLE_MODELS
        ],
    }


@app.get("/health")
async def health():
    return {"status": "ok", "vertexai_base_url": VERTEXAI_BASE_URL}


# Models — serve static list (VertexAI doesn't support OpenAI /models listing).
# Routes with and without /v1 prefix for OpenWebUI compatibility.
@app.get("/v1/models")
@app.get("/models")
async def list_models(request: Request):
    _verify_api_key(request)
    return JSONResponse(content=_build_models_response())


# Chat completions — proxy to VertexAI.
@app.post("/v1/chat/completions")
@app.post("/chat/completions")
async def chat_completions(request: Request):
    _verify_api_key(request)
    body = await request.json()
    token = _get_access_token()
    stream = body.get("stream", False)

    if stream:
        return StreamingResponse(
            _stream_response(token, f"{VERTEXAI_BASE_URL}/chat/completions", body),
            media_type="text/event-stream",
            headers={"Cache-Control": "no-cache", "Connection": "keep-alive"},
        )

    async with httpx.AsyncClient(timeout=300.0) as client:
        resp = await client.post(
            f"{VERTEXAI_BASE_URL}/chat/completions",
            json=body,
            headers={
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json",
            },
        )
    return JSONResponse(content=resp.json(), status_code=resp.status_code)


async def _stream_response(token: str, url: str, body: dict):
    """Stream the VertexAI response back to the client."""
    async with httpx.AsyncClient(timeout=300.0) as client:
        async with client.stream(
            "POST",
            url,
            json=body,
            headers={
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json",
            },
        ) as resp:
            async for chunk in resp.aiter_text():
                yield chunk


# Embeddings — proxy to VertexAI.
@app.post("/v1/embeddings")
@app.post("/embeddings")
async def embeddings(request: Request):
    _verify_api_key(request)
    body = await request.json()
    token = _get_access_token()

    async with httpx.AsyncClient(timeout=300.0) as client:
        resp = await client.post(
            f"{VERTEXAI_BASE_URL}/embeddings",
            json=body,
            headers={
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json",
            },
        )
    return JSONResponse(content=resp.json(), status_code=resp.status_code)
