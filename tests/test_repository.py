from __future__ import annotations

from collections.abc import Mapping, Sequence
from types import SimpleNamespace
from typing import cast
from unittest.mock import MagicMock

import pytest
from elastic_transport import ApiResponseMeta, HttpHeaders, NodeConfig
from elasticsearch import Elasticsearch, NotFoundError

from backend.elasticsearch.document_id import article_document_id
from backend.models.dictionary import DictionaryArticle
from backend.repositories.articles import ArticleRepository, RepositoryResponseError


def _article(word: str = "ґадалІніюм, ґадалІн") -> DictionaryArticle:
    return DictionaryArticle(line=1, raw=f"raw {word}", word=word, latin="latin")


def _article_source() -> dict[str, object]:
    """A source document matching the explicit index mapping."""
    return {
        "line": 10978,
        "raw": "ґадалІніюм, ґадалІн м. /gadalinijum, gadalin/ - гадолиний (Gd)",
        "word": "ґадалІніюм, ґадалІн",
        "latin": "gadalinijum, gadalin",
        "gender": "м",
        "be_notes": [],
        "ru_notes": ["Gd"],
        "sources": [],
        "is_plural": False,
        "is_proper": False,
        "is_link": False,
        "definitions": [{"number": None, "text": "гадолиний", "ru_notes": ["Gd"]}],
    }


def _hit(doc_id: str) -> dict[str, object]:
    return {"_id": doc_id, "_source": _article_source()}


def _search_body(total: int, hits: Sequence[dict[str, object]]) -> dict[str, object]:
    return {"hits": {"total": total, "hits": list(hits)}}


def _not_found_error() -> NotFoundError:
    meta = ApiResponseMeta(
        status=404,
        http_version="1.1",
        headers=HttpHeaders({}),
        duration=0.001,
        node=NodeConfig(scheme="http", host="localhost", port=9200),
    )
    return NotFoundError("document not found", meta, {"found": False})


def _bulk_response_from_operations(
    operations: Sequence[Mapping[str, object]],
) -> SimpleNamespace:
    """Build a bulk response acknowledging every submitted index operation."""
    docs = [op for op in operations if isinstance(op, Mapping) and "index" in op]
    items = [
        {
            "index": {
                "_index": "dictionary",
                "_id": f"id-{position}",
                "status": 201,
                "result": "created",
            }
        }
        for position in range(len(docs))
    ]
    return SimpleNamespace(body={"errors": False, "items": items})


def test_search_articles_parses_hits_and_total(es_client: MagicMock) -> None:
    es_client.search.return_value = SimpleNamespace(
        body=_search_body(total=42, hits=[_hit("id-1"), _hit("id-2")])
    )
    repository = ArticleRepository(cast(Elasticsearch, es_client), index="dictionary")

    page = repository.search_articles(query="gadalin", page=1, page_size=20)

    assert page.total == 42
    assert [item.id for item in page.items] == ["id-1", "id-2"]
    assert page.items[0].data.word == "ґадалІніюм, ґадалІн"
    es_client.search.assert_called_once()


def test_search_articles_passes_pagination_and_query(es_client: MagicMock) -> None:
    captured: dict[str, object] = {}

    def capture_search(**kwargs: object) -> SimpleNamespace:
        captured.update(kwargs)
        return SimpleNamespace(body=_search_body(total=0, hits=[]))

    es_client.search.side_effect = capture_search
    repository = ArticleRepository(cast(Elasticsearch, es_client), index="dictionary")

    repository.search_articles(query="gadalin", page=3, page_size=50)

    assert captured["index"] == "dictionary"
    assert captured["from_"] == 100
    assert captured["size"] == 50
    assert captured["track_total_hits"] is True
    assert captured["rest_total_hits_as_int"] is True
    assert captured["sort"] == ({"line": "asc"},)
    assert isinstance(captured["query"], Mapping)
    assert "bool" in captured["query"]


def test_search_articles_trims_blank_query(es_client: MagicMock) -> None:
    captured: dict[str, object] = {}

    def capture_search(**kwargs: object) -> SimpleNamespace:
        captured.update(kwargs)
        return SimpleNamespace(body=_search_body(total=0, hits=[]))

    es_client.search.side_effect = capture_search
    repository = ArticleRepository(cast(Elasticsearch, es_client), index="dictionary")

    repository.search_articles(query="   ", page=1, page_size=20)

    assert captured["query"] == {"match_all": {}}


def test_search_articles_uses_match_all_for_none_query(es_client: MagicMock) -> None:
    captured: dict[str, object] = {}

    def capture_search(**kwargs: object) -> SimpleNamespace:
        captured.update(kwargs)
        return SimpleNamespace(body=_search_body(total=7, hits=[]))

    es_client.search.side_effect = capture_search
    repository = ArticleRepository(cast(Elasticsearch, es_client), index="dictionary")

    page = repository.search_articles(query=None, page=1, page_size=20)

    assert page.total == 7
    assert captured["query"] == {"match_all": {}}


def test_search_articles_rejects_non_positive_pagination(es_client: MagicMock) -> None:
    repository = ArticleRepository(cast(Elasticsearch, es_client), index="dictionary")

    with pytest.raises(ValueError):
        repository.search_articles(query=None, page=0, page_size=20)
    with pytest.raises(ValueError):
        repository.search_articles(query=None, page=1, page_size=0)


def test_search_articles_raises_on_malformed_response(es_client: MagicMock) -> None:
    es_client.search.return_value = SimpleNamespace(body={"unexpected": True})
    repository = ArticleRepository(cast(Elasticsearch, es_client), index="dictionary")

    with pytest.raises(RepositoryResponseError):
        repository.search_articles(query=None, page=1, page_size=20)


def test_get_article_returns_stored_article(es_client: MagicMock) -> None:
    es_client.get.return_value = SimpleNamespace(body={"_source": _article_source()})
    repository = ArticleRepository(cast(Elasticsearch, es_client), index="dictionary")

    stored = repository.get_article("id-1")

    assert stored is not None
    assert stored.id == "id-1"
    assert stored.data.word == "ґадалІніюм, ґадалІн"
    assert stored.data.gender == "м"
    es_client.get.assert_called_once_with(index="dictionary", id="id-1")


def test_get_article_returns_none_when_missing(es_client: MagicMock) -> None:
    es_client.get.side_effect = _not_found_error()
    repository = ArticleRepository(cast(Elasticsearch, es_client), index="dictionary")

    assert repository.get_article("missing") is None


def test_get_article_raises_on_missing_source(es_client: MagicMock) -> None:
    es_client.get.return_value = SimpleNamespace(body={"found": True})
    repository = ArticleRepository(cast(Elasticsearch, es_client), index="dictionary")

    with pytest.raises(RepositoryResponseError):
        repository.get_article("id-1")


def test_bulk_index_sends_deterministic_document_ids(es_client: MagicMock) -> None:
    es_client.bulk.return_value = SimpleNamespace(
        body={
            "errors": False,
            "items": [
                {
                    "index": {
                        "_index": "dictionary",
                        "_id": "doc-a",
                        "status": 201,
                        "result": "created",
                    }
                },
                {
                    "index": {
                        "_index": "dictionary",
                        "_id": "doc-b",
                        "status": 200,
                        "result": "updated",
                    }
                },
            ],
        }
    )
    repository = ArticleRepository(cast(Elasticsearch, es_client), index="dictionary")
    articles = [_article(word="першае слова"), _article(word="другое слова")]

    result = repository.bulk_index(articles, batch_size=10)

    assert result.indexed == 2
    assert result.failed == 0
    assert result.errors == ()
    es_client.bulk.assert_called_once()

    operations = es_client.bulk.call_args.kwargs["operations"]
    assert isinstance(operations, list)
    assert len(operations) == 4  # two documents: action metadata + source each

    action_meta = operations[0]
    assert isinstance(action_meta, Mapping)
    index_meta = action_meta.get("index")
    assert isinstance(index_meta, Mapping)
    assert index_meta.get("_index") == "dictionary"
    assert index_meta.get("_id") == article_document_id(articles[0])

    source = operations[1]
    assert isinstance(source, Mapping)
    assert source.get("word") == articles[0].word


def test_bulk_index_splits_into_batches(es_client: MagicMock) -> None:
    batch_sizes: list[int] = []

    def capture_bulk(**kwargs: object) -> SimpleNamespace:
        operations = kwargs["operations"]
        assert isinstance(operations, list)
        batch_sizes.append(len(operations))
        return _bulk_response_from_operations(operations)

    es_client.bulk.side_effect = capture_bulk
    repository = ArticleRepository(cast(Elasticsearch, es_client), index="dictionary")
    articles = [_article(word=f"слова-{index}") for index in range(5)]

    result = repository.bulk_index(articles, batch_size=2)

    assert result.indexed == 5
    assert result.failed == 0
    assert batch_sizes == [4, 4, 2]  # three bulk requests of 2/2/1 documents


def test_bulk_index_reports_failed_items(es_client: MagicMock) -> None:
    def failing_bulk(**kwargs: object) -> SimpleNamespace:
        operations = kwargs["operations"]
        assert isinstance(operations, list)
        docs = [op for op in operations if isinstance(op, Mapping) and "index" in op]
        items = [
            {
                "index": {
                    "_index": "dictionary",
                    "_id": f"id-{position}",
                    "status": 400,
                    "error": {
                        "type": "mapper_parsing_exception",
                        "reason": "failed to parse field",
                    },
                }
            }
            for position in range(len(docs))
        ]
        return SimpleNamespace(body={"errors": True, "items": items})

    es_client.bulk.side_effect = failing_bulk
    repository = ArticleRepository(cast(Elasticsearch, es_client), index="dictionary")

    result = repository.bulk_index([_article()], batch_size=5)

    assert result.indexed == 0
    assert result.failed == 1
    assert "mapper_parsing_exception" in result.errors[0]


def test_bulk_index_with_no_articles_does_not_call_elasticsearch(
    es_client: MagicMock,
) -> None:
    repository = ArticleRepository(cast(Elasticsearch, es_client), index="dictionary")

    result = repository.bulk_index([], batch_size=5)

    assert result.indexed == 0
    assert result.failed == 0
    es_client.bulk.assert_not_called()


def test_bulk_index_rejects_non_positive_batch_size(es_client: MagicMock) -> None:
    repository = ArticleRepository(cast(Elasticsearch, es_client), index="dictionary")

    with pytest.raises(ValueError):
        repository.bulk_index([], batch_size=0)
