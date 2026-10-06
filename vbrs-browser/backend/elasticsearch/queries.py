"""Whole-name prefix search; keyword fields prevent matching later words."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Final

SORT_CLAUSES: Final = ({"line": "asc"},)
"""Deterministic ordering by the source's unique line number."""


def search_query(query: str) -> Mapping[str, object]:
    prefix = query.strip().lower()
    return {
        "bool": {
            "should": [
                {"prefix": {"word.keyword": {"value": prefix}}},
                {"prefix": {"latin.keyword": {"value": prefix}}},
            ],
            "minimum_should_match": 1,
        }
    }


def match_all_query() -> Mapping[str, object]:
    return {"match_all": {}}
