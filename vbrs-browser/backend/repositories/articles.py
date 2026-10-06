from __future__ import annotations

import logging
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass
from typing import cast

from elasticsearch import ApiError, Elasticsearch, NotFoundError, TransportError

from backend.config.settings import MAX_ES_RESULT_WINDOW, get_settings
from backend.elasticsearch.document_id import article_document_id
from backend.elasticsearch.queries import SORT_CLAUSES, match_all_query, search_query
from backend.models.dictionary import DictionaryArticle

logger = logging.getLogger(__name__)

# HTTP status codes Elasticsearch reports for a successful bulk item.
_BULK_SUCCESS_STATUSES = frozenset({200, 201})


class RepositoryResponseError(RuntimeError):
    pass


@dataclass(frozen=True, slots=True)
class StoredArticle:
    id: str
    data: DictionaryArticle


@dataclass(frozen=True, slots=True)
class ArticlePage:
    items: list[StoredArticle]
    total: int


@dataclass(frozen=True, slots=True)
class BulkIndexResult:
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
        :func:`backend.elasticsearch.document_id.article_document_id`, which makes
        the operation idempotent: re-importing the same source data updates
        the existing documents instead of creating duplicates.
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
        """Search headword/transliteration prefixes, or list all articles when blank.

        ``None`` or a blank ``query`` returns a deterministic paginated listing
        of all articles.
        """
        if page < 1 or page_size < 1:
            raise ValueError("page and page_size must be positive")
        if page_size > MAX_ES_RESULT_WINDOW:
            raise ValueError("page_size exceeds the Elasticsearch result window")

        es_query = match_all_query()
        if query is not None and query.strip():
            es_query = search_query(query.strip())

        offset = (page - 1) * page_size
        if offset + page_size > MAX_ES_RESULT_WINDOW:
            return self._search_deep_page(es_query, offset, page_size)

        response = self._client.search(
            index=self._index,
            query=es_query,
            sort=SORT_CLAUSES,
            from_=offset,
            size=page_size,
            track_total_hits=True,
            rest_total_hits_as_int=True,
        )
        body = cast(Mapping[str, object], response.body)
        return _parse_search_body(body)

    def _search_deep_page(
        self, query: Mapping[str, object], offset: int, page_size: int
    ) -> ArticlePage:
        keep_alive = f"{get_settings().es_pit_keep_alive_seconds}s"
        opened = self._client.open_point_in_time(index=self._index, keep_alive=keep_alive)
        pit_id = opened.body.get("id")
        if not isinstance(pit_id, str) or not pit_id:
            raise RepositoryResponseError("snapshot response is missing the 'id' field")

        remaining = offset
        cursor: list[object] | None = None
        try:
            while True:
                # Only cursor metadata is fetched while skipping to a numbered page.
                response = self._client.search(
                    pit={"id": pit_id, "keep_alive": keep_alive},
                    query=query,
                    sort=SORT_CLAUSES,
                    search_after=cursor,
                    size=min(remaining, MAX_ES_RESULT_WINDOW) if remaining else page_size,
                    source=remaining == 0,
                    track_total_hits=True,
                    rest_total_hits_as_int=True,
                    allow_partial_search_results=False,
                )
                body = cast(Mapping[str, object], response.body)
                refreshed_id = body.get("pit_id")
                if isinstance(refreshed_id, str) and refreshed_id:
                    pit_id = refreshed_id
                hits, total = _parse_search_hits(body)
                if offset >= total:
                    return ArticlePage(items=[], total=total)
                if remaining == 0:
                    return ArticlePage(items=[_parse_hit(hit) for hit in hits], total=total)
                if not hits or len(hits) > remaining:
                    raise RepositoryResponseError("snapshot returned an inconsistent page boundary")
                last_hit = hits[-1]
                sort_values = last_hit.get("sort") if isinstance(last_hit, Mapping) else None
                if not isinstance(sort_values, list) or not sort_values or sort_values == cursor:
                    raise RepositoryResponseError("search hit is missing a progressing sort cursor")
                cursor = sort_values
                remaining -= len(hits)
        finally:
            try:
                self._client.close_point_in_time(id=pit_id)
            except (ApiError, TransportError):
                # The TTL remains a backstop if cleanup fails; preserve the search outcome.
                logger.warning("Could not close pagination snapshot", exc_info=True)

    def get_article(self, article_id: str) -> StoredArticle | None:
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
        return StoredArticle(id=article_id, data=DictionaryArticle.model_validate(raw_source))

    def _send_bulk(self, operations: Sequence[Mapping[str, object]]) -> BulkIndexResult:
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
    hits, total = _parse_search_hits(body)
    return ArticlePage(items=[_parse_hit(raw_hit) for raw_hit in hits], total=total)


def _parse_search_hits(body: Mapping[str, object]) -> tuple[list[object], int]:
    if body.get("timed_out") is True:
        raise RepositoryResponseError("search timed out before completing the page")
    raw_hits_mapping = body.get("hits")
    if not isinstance(raw_hits_mapping, Mapping):
        raise RepositoryResponseError("search response is missing the 'hits' object")

    hits = raw_hits_mapping.get("hits")
    raw_total = raw_hits_mapping.get("total")
    if not isinstance(hits, list):
        raise RepositoryResponseError("search response is missing the 'hits' list")
    if not isinstance(raw_total, int):
        raise RepositoryResponseError("search response is missing the total hit count")

    return hits, raw_total


def _parse_hit(raw_hit: object) -> StoredArticle:
    if not isinstance(raw_hit, Mapping):
        raise RepositoryResponseError(f"malformed search hit: {raw_hit!r}")

    article_id = raw_hit.get("_id")
    raw_source = raw_hit.get("_source")
    if not isinstance(article_id, str):
        raise RepositoryResponseError("search hit is missing the '_id' field")
    if not isinstance(raw_source, Mapping):
        raise RepositoryResponseError(f"search hit {article_id!r} is missing the '_source' field")

    return StoredArticle(id=article_id, data=DictionaryArticle.model_validate(raw_source))
