"""Lazy Elasticsearch client access.

The client is created on first use so the backend can start and answer the
health endpoint even when Elasticsearch is not yet available; connection
problems surface as ping failures instead of startup crashes.
"""

from __future__ import annotations

from functools import lru_cache

from elasticsearch import Elasticsearch

from api.config.settings import get_settings


@lru_cache(maxsize=1)
def get_elasticsearch_client() -> Elasticsearch:
    """Return a process-wide :class:`Elasticsearch` client from settings."""
    settings = get_settings()
    return Elasticsearch(
        settings.es_url,
        request_timeout=settings.es_request_timeout,
    )


def ping_elasticsearch() -> bool:
    """Return whether the configured Elasticsearch cluster is reachable."""
    settings = get_settings()
    return get_elasticsearch_client().options(
        request_timeout=settings.es_connect_timeout
    ).ping()