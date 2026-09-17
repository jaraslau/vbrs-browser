"""FastAPI application entrypoint for the vbrs-browser backend.

The app is deliberately small: configuration is loaded once from
:mod:`api.config.settings` and CORS is wired from settings. Feature routers
are mounted under the versioned ``/api/v1`` prefix by later modules.
"""

from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api.config.settings import get_settings
from api.elasticsearch.client import ping_elasticsearch

settings = get_settings()

app = FastAPI(
    title="vbrs-browser API",
    description="Read-only dictionary browser API backed by Elasticsearch.",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get(f"{settings.api_v1_prefix}/health", tags=["system"])
def health() -> dict[str, str]:
    """Return service status and Elasticsearch connectivity."""
    return {
        "status": "ok",
        "elasticsearch": "connected" if ping_elasticsearch() else "unavailable",
    }