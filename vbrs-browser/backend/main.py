from __future__ import annotations

import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.config.settings import get_settings
from backend.elasticsearch.client import get_elasticsearch_client
from backend.errors import register_exception_handlers
from backend.routers import articles_router, health_router

logger = logging.getLogger(__name__)

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Closes the shared Elasticsearch connection pool on shutdown.

    No cluster connection is opened at startup: the client is built lazily on
    first use so an unreachable Elasticsearch can never stop the process from
    booting and answering health probes.
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
    application = FastAPI(
        title="vbrs-browser API",
        description=(
            "Read-only dictionary browser API backed by Elasticsearch. "
            "Interactive documentation is enabled for development."
        ),
        version="0.1.0",
        lifespan=lifespan,
    )

    # Origins are configuration-driven; a wildcard would expose the API to
    # every origin the browser happens to load it from.
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
