"""Lazy Elasticsearch client access.

The client is created on first use so the backend can start and answer the
health endpoint even when Elasticsearch is not yet available; connection
problems surface as ping failures instead of startup crashes.
"""

from __future__ import annotations

from functools import lru_cache

from elasticsearch import Elasticsearch

from backend.config.settings import get_settings


@lru_cache(maxsize=1)
def get_elasticsearch_client() -> Elasticsearch:
    settings = get_settings()
    auth: tuple[str, str] | None = (
        (settings.es_username, settings.es_password.get_secret_value())
        if settings.es_username and settings.es_password
        else None
    )
    if settings.es_verify_certs and settings.es_ca_certs:
        return Elasticsearch(
            settings.es_url,
            request_timeout=settings.es_request_timeout,
            basic_auth=auth,
            verify_certs=True,
            ca_certs=settings.es_ca_certs,
        )
    return Elasticsearch(
        settings.es_url,
        request_timeout=settings.es_request_timeout,
        basic_auth=auth,
        verify_certs=settings.es_verify_certs,
    )


def ping_elasticsearch() -> bool:
    settings = get_settings()
    return get_elasticsearch_client().options(request_timeout=settings.es_connect_timeout).ping()
