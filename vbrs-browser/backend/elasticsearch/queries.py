"""Keyword fields compare whole names, preserving spaces and punctuation."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Final

from backend.config.settings import get_settings

SEARCH_FIELDS: Final = ("word.keyword", "latin.keyword")
PREFIX_MATCH_SCORE: Final = 2.0
FUZZY_MATCH_SCORE: Final = 1.0
SORT_CLAUSES: Final = ({"_score": "desc"}, {"line": "asc"})


def search_query(query: str) -> Mapping[str, object]:
    value = query.strip().lower()
    settings = get_settings()
    prefixes = {
        "bool": {
            "should": [{"prefix": {field: {"value": value}}} for field in SEARCH_FIELDS],
            "minimum_should_match": 1,
        }
    }
    fuzzy_matches = {
        "bool": {
            "should": [
                {
                    "fuzzy": {
                        field: {
                            "value": value,
                            "fuzziness": settings.search_fuzziness,
                            "max_expansions": settings.search_fuzzy_max_expansions,
                            "prefix_length": 0,
                            "transpositions": True,
                        }
                    }
                }
                for field in SEARCH_FIELDS
            ],
            "minimum_should_match": 1,
        }
    }
    # Fixed tiers keep every prefix ahead of fuzzy hits, even across both scripts.
    return {
        "dis_max": {
            "queries": [
                {"constant_score": {"filter": prefixes, "boost": PREFIX_MATCH_SCORE}},
                {"constant_score": {"filter": fuzzy_matches, "boost": FUZZY_MATCH_SCORE}},
            ]
        }
    }


def match_all_query() -> Mapping[str, object]:
    return {"match_all": {}}
