"""Tests for the HTTP API Pydantic models."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from api.models.api import (
    ArticleListResponse,
    ArticleResponse,
    ErrorResponse,
    SearchQuery,
)
from api.models.dictionary import DictionaryArticle


def sample_article() -> DictionaryArticle:
    return DictionaryArticle.model_validate(
        {
            "line": 10978,
            "raw": "ґадалІніюм, ґадалІн м. /gadalinijum, gadalin/ - гадолиний (Gd)",
            "word": "ґадалІніюм, ґадалІн",
            "latin": "gadalinijum, gadalin",
            "gender": "м",
            "definitions": [{"number": None, "text": "гадолиний", "ru_notes": ["Gd"]}],
        }
    )


def test_article_response_includes_id_and_article_fields() -> None:
    response = ArticleResponse.from_article("abc123", sample_article())

    dumped = response.model_dump()
    assert dumped["id"] == "abc123"
    assert dumped["word"] == "ґадалІніюм, ґадалІн"
    assert dumped["latin"] == "gadalinijum, gadalin"
    assert dumped["gender"] == "м"
    assert dumped["line"] == 10978
    assert dumped["definitions"][0]["text"] == "гадолиний"


def test_article_response_requires_id() -> None:
    with pytest.raises(ValidationError):
        ArticleResponse.model_validate({**sample_article().model_dump(), "id": None})


def test_article_list_response_serializes_pagination() -> None:
    response = ArticleListResponse(
        items=[ArticleResponse.from_article("abc", sample_article())],
        page=2,
        page_size=20,
        total=1,
    )

    dumped = response.model_dump()
    assert dumped["page"] == 2
    assert dumped["page_size"] == 20
    assert dumped["total"] == 1
    assert dumped["items"][0]["id"] == "abc"


def test_article_list_response_rejects_invalid_pagination() -> None:
    with pytest.raises(ValidationError):
        ArticleListResponse(items=[], page=0, page_size=20, total=0)
    with pytest.raises(ValidationError):
        ArticleListResponse(items=[], page=1, page_size=0, total=0)
    with pytest.raises(ValidationError):
        ArticleListResponse(items=[], page=1, page_size=20, total=-1)


def test_error_response_serializes_detail() -> None:
    assert ErrorResponse(detail="article not found").model_dump() == {
        "detail": "article not found"
    }


def test_search_query_defaults() -> None:
    query = SearchQuery()

    assert query.q is None
    assert query.page == 1
    assert query.page_size is None


def test_search_query_validation() -> None:
    assert SearchQuery(q="gadalin", page=3, page_size=50).page_size == 50

    with pytest.raises(ValidationError):
        SearchQuery(page=0)
    with pytest.raises(ValidationError):
        SearchQuery(page_size=0)