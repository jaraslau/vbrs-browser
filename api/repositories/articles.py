"""Elasticsearch-backed repository for dictionary articles.

The repository is the only layer that talks to Elasticsearch on behalf of the
application. It exposes three operations:

* :meth:`ArticleRepository.bulk_index` -- idempotent batch indexing,
* :meth:`ArticleRepository.search_articles` -- free-text search with
  deterministic pagination,
* :meth:`ArticleRepository.get_article` -- retrieval of a single article by
  its stable document ID.

Elasticsearch responses are parsed into typed domain objects inside this
module; raw response shapes never escape it.
"""

from __future__ import annotations

import logging
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass
from typing import cast

from elasticsearch import Elasticsearch, NotFoundError

from api.elasticsearch.document_id import article_document_id
from api.elasticsearch.queries import SORT_CLAUSES, match_all_query, search_query
from api.models.dictionary import DictionaryArticle

logger = logging.getLogger(__name__)

# HTTP status codes Elasticsearch reports for a successful bulk item.
_BULK_SUCCESS_STATUSES = frozenset({200, 201})


class RepositoryResponseError(RuntimeError):
    """Raised when Elasticsearch returns an unexpected response shape."""


@dataclass(frozen=True, slots=True)
class StoredArticle:
    """A dictionary article paired with its stable Elasticsearch document ID."""

    id: str
    data: DictionaryArticle


@dataclass(frozen=True, slots=True)
class ArticlePage:
    """A single page of search/listing results."""

    items: list[StoredArticle]
    total: int


@dataclass(frozen=True, slots=True)
class BulkIndexResult:
    """Outcome of a bulk indexing operation.

    Attributes:
        indexed: Number of operations acknowledged successfully.
        failed: Number of operations rejected by Elasticsearch.
        errors: Human-readable description of every failed operation.
    """

    indexed: int
    failed: int
    errors: tuple[str, ...]


class ArticleRepository:
    """Data access for dictionary articles stored in Elasticsearch.

    The repository takes an explicit :class:`Elasticsearch` client and index
    name so tests can substitute fakes and callers can target any cluster.
    """

    def __init__(self, client: Elasticsearch, index: str) -> None:
        self._client = client
        self._index = index

    def bulk_index(
        self,
        articles: Iterable[DictionaryArticle],
        *,
        batch_size: int,
    ) -> BulkIndexResult:
        """Index ``articles`` with Elasticsearch's bulk API, in batches.

        Each article is assigned the deterministic ID produced by
        :func:`api.elasticsearch.document_id.article_document_id`, which makes
        the operation idempotent: re-importing the same source data updates
        the existing documents instead of creating duplicates.

        Args:
            articles: Articles to index.
            batch_size: Number of documents sent per bulk request.

        Raises:
            ValueError: When ``batch_size`` is not positive.
        """
        if batch_size < 1:
            raise ValueError("batch_size must be positive")

        indexed = 0
        errors: list[str] = []
        pending: list[Mapping[str, object]] = []

        for article in articles:
            pending.append(
                {
                    "index": {
                        "_index": self._index,
                        "_id": article_document_id(article),
                    }
                }
            )
            pending.append(article.model_dump(mode="json"))
            if len(pending) >= batch_size * 2:
                result = self._send_bulk(pending)
                indexed += result.indexed
                errors.extend(result.errors)
                pending = []

        if pending:
            result = self._send_bulk(pending)
            indexed += result.indexed
            errors.extend(result.errors)

        return BulkIndexResult(indexed=indexed, failed=len(errors), errors=tuple(errors))

    def search_articles(
        self,
        *,
        query: str | None,
        page: int,
        page_size: int,
    ) -> ArticlePage:
        """Search articles by free text, or list all articles when blank.

        Args:
            query: Free-text search query. ``None`` or blank returns a
                deterministic paginated listing of all articles.
            page: 1-based page number.
            page_size: Number of articles per page.

        Raises:
            ValueError: When ``page`` or ``page_size`` is not positive.
        """
        if page < 1 or page_size < 1:
            raise ValueError("page and page_size must be positive")

        es_query = match_all_query()
        if query is not None and query.strip():
            es_query = search_query(query.strip())

        response = self._client.search(
            index=self._index,
            query=es_query,
            sort=SORT_CLAUSES,
            from_=(page - 1) * page_size,
            size=page_size,
            track_total_hits=True,
            rest_total_hits_as_int=True,
        )
        body = cast(Mapping[str, object], response.body)
        return _parse_search_body(body)

    def get_article(self, article_id: str) -> StoredArticle | None:
        """Return the article with ``article_id``, or None if it does not exist."""
        try:
            response = self._client.get(index=self._index, id=article_id)
        except NotFoundError:
            return None

        body = cast(Mapping[str, object], response.body)
        raw_source = body.get("_source")
        if not isinstance(raw_source, Mapping):
            raise RepositoryResponseError(
                f"document {article_id!r} has no '_source' in the get response"
            )
        return StoredArticle(
            id=article_id, data=DictionaryArticle.model_validate(raw_source)
        )

    def _send_bulk(self, operations: Sequence[Mapping[str, object]]) -> BulkIndexResult:
        """Send one bulk request and parse the response into a summary."""
        response = self._client.bulk(operations=operations)
        body = cast(Mapping[str, object], response.body)
        return _parse_bulk_body(body)


def _parse_bulk_body(body: Mapping[str, object]) -> BulkIndexResult:
    """Parse a bulk API response body into a typed result summary.

    The bulk response carries one entry per submitted operation under
    ``items``; each entry is a single-key mapping whose key is the operation
    type (``index``/``create``/``update``/``delete``) and whose value holds
    the per-operation outcome, including the HTTP ``status`` and, on failure,
    an ``error`` object.
    """
    raw_items = body.get("items")
    if not isinstance(raw_items, list):
        raise RepositoryResponseError("bulk response is missing the 'items' list")

    indexed = 0
    errors: list[str] = []
    for raw_item in raw_items:
        if not isinstance(raw_item, Mapping):
            errors.append(f"malformed bulk item: {raw_item!r}")
            continue
        for action, raw_outcome in raw_item.items():
            if not isinstance(raw_outcome, Mapping):
                errors.append(f"{action}: malformed item outcome {raw_outcome!r}")
                continue
            status = raw_outcome.get("status")
            if isinstance(status, int) and status in _BULK_SUCCESS_STATUSES:
                indexed += 1
            else:
                detail = raw_outcome.get("error")
                errors.append(f"{action} failed (status={status}): {detail!r}")

    return BulkIndexResult(indexed=indexed, failed=len(errors), errors=tuple(errors))


def _parse_search_body(body: Mapping[str, object]) -> ArticlePage:
    """Parse a search response body into a typed :class:`ArticlePage`."""
    raw_hits_mapping = body.get("hits")
    if not isinstance(raw_hits_mapping, Mapping):
        raise RepositoryResponseError("search response is missing the 'hits' object")

    hits = raw_hits_mapping.get("hits")
    raw_total = raw_hits_mapping.get("total")
    if not isinstance(hits, list):
        raise RepositoryResponseError("search response is missing the 'hits' list")
    if not isinstance(raw_total, int):
        raise RepositoryResponseError("search response is missing the total hit count")

    return ArticlePage(items=[_parse_hit(raw_hit) for raw_hit in hits], total=raw_total)


def _parse_hit(raw_hit: object) -> StoredArticle:
    """Parse a single search hit into a :class:`StoredArticle`."""
    if not isinstance(raw_hit, Mapping):
        raise RepositoryResponseError(f"malformed search hit: {raw_hit!r}")

    article_id = raw_hit.get("_id")
    raw_source = raw_hit.get("_source")
    if not isinstance(article_id, str):
        raise RepositoryResponseError("search hit is missing the '_id' field")
    if not isinstance(raw_source, Mapping):
        raise RepositoryResponseError(
            f"search hit {article_id!r} is missing the '_source' field"
        )

    return StoredArticle(
        id=article_id, data=DictionaryArticle.model_validate(raw_source)
    )