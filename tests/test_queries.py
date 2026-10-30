from __future__ import annotations

from collections.abc import Mapping

import pytest

from backend.config.settings import Settings
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
def test_search_matches_whole_names_with_prefixes_ahead_of_typos(
    query: str, prefix: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(
        "backend.elasticsearch.queries.get_settings", lambda: Settings(_env_file=None)
    )
    assert search_query(query) == {
        "dis_max": {
            "queries": [
                {
                    "constant_score": {
                        "filter": {
                            "bool": {
                                "should": [
                                    {"prefix": {"word.keyword": {"value": prefix}}},
                                    {"prefix": {"latin.keyword": {"value": prefix}}},
                                ],
                                "minimum_should_match": 1,
                            }
                        },
                        "boost": 2.0,
                    }
                },
                {
                    "constant_score": {
                        "filter": {
                            "bool": {
                                "should": [
                                    {
                                        "fuzzy": {
                                            field: {
                                                "value": prefix,
                                                "fuzziness": "AUTO",
                                                "max_expansions": 50,
                                                "prefix_length": 0,
                                                "transpositions": True,
                                            }
                                        }
                                    }
                                    for field in ("word.keyword", "latin.keyword")
                                ],
                                "minimum_should_match": 1,
                            }
                        },
                        "boost": 1.0,
                    }
                },
            ]
        }
    }


@pytest.mark.parametrize("fuzziness", ["0", "1", "2"])
def test_fuzzy_search_uses_configured_limits(
    monkeypatch: pytest.MonkeyPatch, fuzziness: str
) -> None:
    monkeypatch.setenv("SEARCH_FUZZINESS", fuzziness)
    settings = Settings(_env_file=None, search_fuzzy_max_expansions=10)
    monkeypatch.setattr("backend.elasticsearch.queries.get_settings", lambda: settings)
    query = search_query("слвоа")
    dis_max = query["dis_max"]
    assert isinstance(dis_max, Mapping)
    queries = dis_max["queries"]
    assert isinstance(queries, list)
    for clause in queries[1]["constant_score"]["filter"]["bool"]["should"]:
        for options in clause["fuzzy"].values():
            assert options["fuzziness"] == fuzziness
            assert options["max_expansions"] == 10


def test_match_all_query() -> None:
    assert match_all_query() == {"match_all": {}}
