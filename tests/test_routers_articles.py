"""Tests for the article search and detail HTTP routes."""

from __future__ import annotations

from collections.abc import Sequence
from typing import cast

from elasticsearch import ConnectionError as EsConnectionError
from fastapi.testclient import TestClient

from api.main import create_app
from api.repositories.articles import ArticleRepository, StoredArticle
from api.routers.articles import get_article_repository
from conftest import FakeArticleRepository, stored_article


def _make_client(
    articles: Sequence[StoredArticle] | None = None,
) -> tuple[TestClient, FakeArticleRepository]:
    app = create_app()
    repository = FakeArticleRepository(articles)
    app.dependency_overrides[get_article_repository] = lambda: cast(ArticleRepository, repository)
    return TestClient(app), repository


def _sample_articles() -> list[StoredArticle]:
    return [
        stored_article("id-1", word="ґадалІніюм, ґадалІн"),
        stored_article("id-2", word="ґазаахоўнік"),
        stored_article("id-3", word="адзін"),
    ]


def test_list_articles_returns_deterministic_paginated_listing() -> None:
    client, repository = _make_client(_sample_articles())

    with client:
        response = client.get("/api/v1/articles")

    assert response.status_code == 200
    body = response.json()
    assert body["page"] == 1
    assert body["page_size"] == 20
    assert body["total"] == 3
    assert [item["id"] for item in body["items"]] == ["id-1", "id-2", "id-3"]
    assert repository.search_calls == [(None, 1, 20)]


def test_list_articles_searches_by_query() -> None:
    client, repository = _make_client(_sample_articles())

    with client:
        response = client.get("/api/v1/articles", params={"q": "ґазаахоўнік"})

    assert response.status_code == 200
    body = response.json()
    assert body["total"] == 1
    assert body["items"][0]["id"] == "id-2"
    assert repository.search_calls == [("ґазаахоўнік", 1, 20)]


def test_list_articles_treats_blank_query_as_listing() -> None:
    client, repository = _make_client(_sample_articles())

    with client:
        response = client.get("/api/v1/articles", params={"q": "   "})

    assert response.status_code == 200
    assert response.json()["total"] == 3
    assert repository.search_calls == [("   ", 1, 20)]


def test_list_articles_forwards_pagination_params() -> None:
    client, repository = _make_client(_sample_articles())

    with client:
        response = client.get("/api/v1/articles", params={"q": "а", "page": 2, "page_size": 1})

    assert response.status_code == 200
    body = response.json()
    assert body["page"] == 2
    assert body["page_size"] == 1
    assert repository.search_calls == [("а", 2, 1)]


def test_list_articles_clamps_page_size_to_maximum() -> None:
    client, _ = _make_client(_sample_articles())

    with client:
        response = client.get("/api/v1/articles", params={"page_size": 1000})

    assert response.status_code == 200
    assert response.json()["page_size"] == 100


def test_list_articles_rejects_invalid_page_parameters() -> None:
    client, _ = _make_client(_sample_articles())

    with client:
        response_page_zero = client.get("/api/v1/articles", params={"page": 0})
        response_size_zero = client.get("/api/v1/articles", params={"page_size": 0})
        response_size_negative = client.get("/api/v1/articles", params={"page_size": -5})

    assert response_page_zero.status_code == 422
    assert response_size_zero.status_code == 422
    assert response_size_negative.status_code == 422
    for response in (
        response_page_zero,
        response_size_zero,
        response_size_negative,
    ):
        assert isinstance(response.json()["detail"], list)


def test_get_article_returns_the_requested_article() -> None:
    client, repository = _make_client(_sample_articles())

    with client:
        response = client.get("/api/v1/articles/id-1")

    assert response.status_code == 200
    body = response.json()
    assert body["id"] == "id-1"
    assert body["word"] == "ґадалІніюм, ґадалІн"
    assert repository.get_calls == ["id-1"]


def test_get_article_returns_404_when_missing() -> None:
    client, repository = _make_client([])

    with client:
        response = client.get("/api/v1/articles/missing")

    assert response.status_code == 404
    assert response.json() == {"detail": "Article 'missing' not found"}
    assert repository.get_calls == ["missing"]


def test_list_articles_maps_elasticsearch_failure_to_json_error() -> None:
    app = create_app()

    def failing_repository() -> ArticleRepository:
        raise EsConnectionError("connection refused")

    app.dependency_overrides[get_article_repository] = failing_repository

    with TestClient(app) as client:
        response = client.get("/api/v1/articles")

    assert response.status_code == 503
    assert response.json() == {
        "detail": "The search backend is temporarily unavailable."
    }
