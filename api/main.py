"""FastAPI application entrypoint for the vbrs-browser backend.

The app is deliberately small: configuration is loaded once from
:mod:`api.config.settings`, CORS is wired from settings, exception handlers
that normalize failures into a consistent JSON shape are registered, and the
feature routers are mounted under the versioned ``/api/v1`` prefix.
"""

from __future__ import annotations

import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api.config.settings import get_settings
from api.elasticsearch.client import get_elasticsearch_client
from api.errors import register_exception_handlers
from api.routers import articles_router, health_router

logger = logging.getLogger(__name__)

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Manage the application's lifecycle.

    Startup keeps the process bootable while Elasticsearch is still warming
    up: the Elasticsearch client is created lazily on first use so a missing
    cluster never prevents the health endpoint from answering. Shutdown
    closes the shared Elasticsearch connection pool so the process can exit
    cleanly.
    """
    logger.info("Starting %s", app.title)
    try:
        yield
    finally:
        logger.info("Shutting down %s", app.title)
        client = get_elasticsearch_client()
        client.close()
        get_elasticsearch_client.cache_clear()


def create_app() -> FastAPI:
    """Build and configure the FastAPI application."""
    application = FastAPI(
        title="vbrs-browser API",
        description=(
            "Read-only dictionary browser API backed by Elasticsearch. "
            "Interactive documentation is enabled for development."
        ),
        version="0.1.0",
        lifespan=lifespan,
    )

    # CORS origins come from settings (never a hardcoded wildcard): the
    # frontend and its API client must be explicit, environment-configured
    # origins.
    application.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    register_exception_handlers(application)

    application.include_router(health_router, prefix=settings.api_v1_prefix)
    application.include_router(articles_router, prefix=settings.api_v1_prefix)

    return application


app = create_app()
