from __future__ import annotations

from collections.abc import Sequence
from unittest.mock import MagicMock

import pytest

from backend.models.dictionary import DictionaryArticle
from backend.repositories.articles import ArticlePage, StoredArticle


@pytest.fixture
def es_client() -> MagicMock:
    return MagicMock()


def stored_article(
    article_id: str = "id-1",
    word: str = "ґадалІніюм, ґадалІн",
    latin: str = "gadalinijum, gadalin",
) -> StoredArticle:
    return StoredArticle(
        id=article_id,
        data=DictionaryArticle(
            line=10978,
            raw=f"raw {word}",
            word=word,
            latin=latin,
        ),
    )


class FakeArticleRepository:
    """In-memory repository stand-in.

    Records every call so tests can assert on the arguments the service
    forwards to the data-access layer, and filters/paginates synchronously so
    router tests exercise the full router -> service -> repository wiring
    without touching Elasticsearch.
    """

    def __init__(self, articles: Sequence[StoredArticle] | None = None) -> None:
        self._articles: list[StoredArticle] = list(articles or [])
        self.search_calls: list[tuple[str | None, int, int]] = []
        self.get_calls: list[str] = []

    def search_articles(
        self,
        *,
        query: str | None,
        page: int,
        page_size: int,
    ) -> ArticlePage:
        self.search_calls.append((query, page, page_size))
        if query is None or not query.strip():
            matches = list(self._articles)
        else:
            needle = query.strip().lower()
            matches = [
                stored
                for stored in self._articles
                if needle in stored.data.word.lower() or needle in stored.data.latin.lower()
            ]
        start = (page - 1) * page_size
        return ArticlePage(
            items=matches[start : start + page_size],
            total=len(matches),
        )

    def get_article(self, article_id: str) -> StoredArticle | None:
        self.get_calls.append(article_id)
        for stored in self._articles:
            if stored.id == article_id:
                return stored
        return None
