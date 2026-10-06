from __future__ import annotations

import pytest

from backend.elasticsearch.queries import match_all_query, search_query


@pytest.mark.parametrize(
    ("query", "prefix"),
    [
        ("ч", "ч"),
        (" ЧАС ", "час"),
        ("ča", "ča"),
        (" ČAS ", "čas"),
        ("з час", "з час"),
        ("z čas", "z čas"),
        ("ч*", "ч*"),
    ],
)
def test_search_only_prefixes_whole_headword_and_transliteration(query: str, prefix: str) -> None:
    # Text-field queries would also match the second token of "з часам".
    assert search_query(query) == {
        "bool": {
            "should": [
                {"prefix": {"word.keyword": {"value": prefix}}},
                {"prefix": {"latin.keyword": {"value": prefix}}},
            ],
            "minimum_should_match": 1,
        }
    }


def test_match_all_query() -> None:
    assert match_all_query() == {"match_all": {}}
