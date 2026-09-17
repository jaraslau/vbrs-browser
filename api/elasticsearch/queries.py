"""Typed construction of the Elasticsearch query DSL for article search.

Queries are produced as plain nested mappings in the shape Elasticsearch
expects; every function returns a fresh mapping so callers can reuse it
safely. Field relevance is expressed through per-field boosts, implementing
the documented ordering:

    exact word match > prefix/close word match > latin match
    > definition match > raw-text match
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Final

WORD_BOOST: Final = 6.0
"""Boost for a full word match (highest relevance)."""

WORD_PREFIX_BOOST: Final = 4.0
"""Boost for a prefix/close word match against the headword."""

LATIN_BOOST: Final = 3.0
"""Boost for a match against the latin transliteration."""

DEFINITION_BOOST: Final = 2.0
"""Boost for a match against definition text."""

RAW_BOOST: Final = 1.0
"""Boost for a match against the original raw article text."""

SORT_CLAUSES: Final = ({"line": "asc"}, {"_id": "asc"})
"""Deterministic ordering for paginated result listings."""


def _match(field: str, query: str, boost: float) -> Mapping[str, object]:
    return {"match": {field: {"query": query, "boost": boost}}}


def search_query(query: str) -> Mapping[str, object]:
    return {
        "bool": {
            "should": [
                _match("word", query, WORD_BOOST),
                {
                    "match_phrase_prefix": {
                        "word": {"query": query, "boost": WORD_PREFIX_BOOST}
                    }
                },
                _match("latin", query, LATIN_BOOST),
                _match("definitions.text", query, DEFINITION_BOOST),
                _match("raw", query, RAW_BOOST),
            ],
            "minimum_should_match": 1,
        }
    }


def match_all_query() -> Mapping[str, object]:
    return {"match_all": {}}