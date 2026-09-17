"""Explicit Elasticsearch index mapping for dictionary articles.

The index is created explicitly instead of relying on Elasticsearch dynamic
mapping so the schema stays reviewable, search behavior stays predictable,
and unknown fields fail indexing instead of silently appearing in documents
(``dynamic: strict``).

Search analyzers
----------------
``text_analyzer`` is a custom analyzer (standard tokenizer and lowercase
filter) applied to every free-text field (``word``, ``latin``, ``raw`` and
definition text). The standard tokenizer keeps Cyrillic and Latin words as
single tokens, and the lowercase filter makes matching case-insensitive at
both index time and query time.

``gender`` and ``sources`` are mapped as keywords (exact values), the boolean
flags are mapped as booleans, and ``line`` is an integer used for
deterministic ordering.

Field relevance is controlled at query time in :mod:`api.elasticsearch.queries`:
``word`` and ``latin`` are boosted above definition text and the raw line.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Final, cast

from elasticsearch import Elasticsearch
from elasticsearch.exceptions import BadRequestError

from api.config.settings import get_settings
from api.elasticsearch.client import get_elasticsearch_client

# Custom analyzer: standard tokenizer + lowercase filter. Applied to every
# free-text field so Cyrillic/Latin words are tokenized naturally and search
# is case-insensitive.
INDEX_SETTINGS: Final[Mapping[str, object]] = {
    "index": {
        "analysis": {
            "analyzer": {
                "text_analyzer": {
                    "type": "custom",
                    "tokenizer": "standard",
                    "filter": ["lowercase"],
                },
            },
            "normalizer": {
                "case_normalizer": {
                    "type": "custom",
                    "filter": ["lowercase"],
                },
            },
        },
    },
}

INDEX_MAPPING: Final[Mapping[str, object]] = {
    "dynamic": "strict",
    "properties": {
        "line": {"type": "integer"},
        "raw": {"type": "text", "analyzer": "text_analyzer"},
        "word": {
            "type": "text",
            "analyzer": "text_analyzer",
            "fields": {
                "keyword": {"type": "keyword", "normalizer": "case_normalizer"},
            },
        },
        "latin": {
            "type": "text",
            "analyzer": "text_analyzer",
            "fields": {
                "keyword": {"type": "keyword", "normalizer": "case_normalizer"},
            },
        },
        "gender": {"type": "keyword"},
        "is_plural": {"type": "boolean"},
        "is_proper": {"type": "boolean"},
        "is_link": {"type": "boolean"},
        "be_notes": {"type": "text", "analyzer": "text_analyzer"},
        "ru_notes": {"type": "text", "analyzer": "text_analyzer"},
        "sources": {"type": "keyword"},
        "definitions": {
            "type": "object",
            "properties": {
                "number": {"type": "integer"},
                "text": {"type": "text", "analyzer": "text_analyzer"},
                "ru_notes": {"type": "text", "analyzer": "text_analyzer"},
            },
        },
    },
}


def create_index_if_missing(client: Elasticsearch, index: str) -> bool:
    """Create ``index`` with the explicit mapping unless it already exists.

    Returns True when the index was created, False when it already existed.
    """
    if client.indices.exists(index=index):
        return False
    try:
        client.indices.create(
            index=index, settings=INDEX_SETTINGS, mappings=INDEX_MAPPING
        )
    except BadRequestError as exc:
        # Another process created the index between exists() and create();
        # Elasticsearch then rejects the request with
        # ``resource_already_exists_exception``. Any other failure is real
        # and must propagate.
        if _is_resource_already_exists(exc):
            return False
        raise
    return True


def recreate_index(client: Elasticsearch, index: str) -> None:
    """Delete ``index`` if present, then recreate it with the explicit mapping."""
    if client.indices.exists(index=index):
        client.indices.delete(index=index)
    client.indices.create(index=index, settings=INDEX_SETTINGS, mappings=INDEX_MAPPING)


def ensure_article_index(recreate: bool = False) -> bool:
    """Ensure the configured article index exists.

    Convenience wrapper wired to the global settings and Elasticsearch client;
    used by the ingestion command-line script. Returns True when the index was
    created (or recreated).
    """
    client = get_elasticsearch_client()
    index = get_settings().es_index
    if recreate:
        recreate_index(client, index)
        return True
    return create_index_if_missing(client, index)


def _is_resource_already_exists(exc: BadRequestError) -> bool:
    """Return True when a create failure means the index already exists."""
    body = cast(Mapping[str, object], exc.body)
    error = body.get("error")
    if isinstance(error, Mapping):
        return error.get("type") == "resource_already_exists_exception"
    return False