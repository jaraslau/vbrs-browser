from __future__ import annotations

from typing import cast

import pytest

from api.config.settings import Settings
from api.models.api import SearchQuery
from api.repositories.articles import ArticleRepository
from api.services.articles import ArticleNotFoundError, ArticleService
from conftest import FakeArticleRepository, stored_article


def _make_service(
    repository: FakeArticleRepository | None = None,
    settings: Settings | None = None,
) -> tuple[ArticleService, FakeArticleRepository]:
    fake = repository or FakeArticleRepository(
        [
            stored_article("id-1", word="ґадалІніюм, ґадалІн"),
            stored_article("id-2", word="другое", latin="druhaje"),
        ]
    )
    return (
        ArticleService(
            repository=cast(ArticleRepository, fake),
            settings=settings or Settings(_env_file=None),
        ),
        fake,
    )


def test_search_applies_default_page_size_when_omitted() -> None:
    service, repository = _make_service()

    response = service.search(SearchQuery())

    assert response.page == 1
    assert response.page_size == 20
    assert response.total == 2
    assert [item.id for item in response.items] == ["id-1", "id-2"]
    assert repository.search_calls == [(None, 1, 20)]


def test_search_clamps_page_size_to_configured_maximum() -> None:
    settings = Settings(_env_file=None, page_size=20, max_page_size=100)
    service, repository = _make_service(settings=settings)

    response = service.search(SearchQuery(page_size=500))

    assert response.page_size == 100
    assert repository.search_calls == [(None, 1, 100)]


def test_search_passes_query_and_pagination_to_repository() -> None:
    service, repository = _make_service()

    service.search(SearchQuery(q="gadalin", page=3, page_size=50))

    assert repository.search_calls == [("gadalin", 3, 50)]


def test_search_maps_stored_articles_to_response_models() -> None:
    service, _ = _make_service()

    response = service.search(SearchQuery(q="gadalin"))

    assert response.items[0].id == "id-1"
    assert response.items[0].word == "ґадалІніюм, ґадалІн"
    assert response.total == 1


def test_get_article_returns_full_article() -> None:
    service, repository = _make_service()

    response = service.get_article("id-2")

    assert response.id == "id-2"
    assert response.word == "другое"
    assert repository.get_calls == ["id-2"]


def test_get_article_raises_not_found_for_missing_article() -> None:
    service, repository = _make_service()

    with pytest.raises(ArticleNotFoundError) as exc_info:
        service.get_article("missing")

    assert exc_info.value.article_id == "missing"
    assert repository.get_calls == ["missing"]
