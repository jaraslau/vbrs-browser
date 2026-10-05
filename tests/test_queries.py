from __future__ import annotations

from collections.abc import Mapping

from backend.elasticsearch.queries import (
    DEFINITION_BOOST,
    LATIN_BOOST,
    RAW_BOOST,
    WORD_BOOST,
    WORD_PREFIX_BOOST,
    match_all_query,
    search_query,
)

EXPECTED_FIELDS = {"word", "latin", "definitions.text", "raw"}


def _search_body(query: str) -> Mapping[str, object]:
    return search_query(query)


def test_search_query_uses_bool_should_with_minimum_one() -> None:
    body = _search_body("gadalin")

    bool_mapping = body.get("bool")
    assert isinstance(bool_mapping, Mapping)
    assert bool_mapping.get("minimum_should_match") == 1


def test_search_query_covers_all_searchable_fields() -> None:
    body = _search_body("gadalin")

    bool_mapping = body.get("bool")
    assert isinstance(bool_mapping, Mapping)
    should = bool_mapping.get("should")
    assert isinstance(should, list)

    fields: set[str] = set()
    for clause in should:
        assert isinstance(clause, Mapping)
        for inner in clause.values():
            assert isinstance(inner, Mapping)
            fields.update(str(field) for field in inner)

    assert fields >= EXPECTED_FIELDS


def test_search_query_boosts_follow_relevance_order() -> None:
    # word/latin must outrank definition text and the raw line
    assert WORD_BOOST > LATIN_BOOST > DEFINITION_BOOST > RAW_BOOST
    assert WORD_PREFIX_BOOST > LATIN_BOOST


def test_word_clauses_are_included() -> None:
    body = _search_body("gadalin")

    bool_mapping = body.get("bool")
    assert isinstance(bool_mapping, Mapping)
    should = bool_mapping.get("should")
    assert isinstance(should, list)

    clause_types = {next(iter(clause)) for clause in should if isinstance(clause, Mapping)}
    assert "match" in clause_types
    assert "match_phrase_prefix" in clause_types


def test_match_all_query() -> None:
    assert match_all_query() == {"match_all": {}}
