from __future__ import annotations

import json
from collections.abc import Mapping, Sequence
from pathlib import Path
from types import SimpleNamespace
from typing import cast
from unittest.mock import MagicMock

import pytest
from elasticsearch import Elasticsearch

from backend.config.settings import Settings
from backend.models.dictionary import DictionaryArticle
from backend.repositories.articles import ArticleRepository
from scripts.import_dictionary import (
    DictionaryFileError,
    build_argument_parser,
    dataset_fingerprint,
    import_file,
    in_batches,
    main,
    run,
    validate_dictionary_file,
)


def _article_dict(word: str = "ґадалІніюм", line: int = 10978) -> dict[str, object]:
    return {
        "line": line,
        "raw": f"{word} м. /gadalin/ - гадолиний (Gd)",
        "word": word,
        "latin": "gadalin",
        "gender": "м",
        "is_plural": False,
        "is_proper": False,
        "is_link": False,
        "be_notes": [],
        "ru_notes": [],
        "sources": [],
        "definitions": [],
    }


def _write_file(path: Path, payload: object) -> Path:
    path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
    return path


def _article(line: int = 1, word: str = "слова") -> DictionaryArticle:
    return DictionaryArticle(line=line, raw=f"raw {word}", word=word, latin="latin")


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


def _bulk_rejecting_response(
    operations: Sequence[Mapping[str, object]],
) -> SimpleNamespace:
    """Build a bulk response in which every operation fails."""
    docs = [op for op in operations if isinstance(op, Mapping) and "index" in op]
    items = [
        {
            "index": {
                "_index": "dictionary",
                "_id": f"id-{position}",
                "status": 400,
                "error": {"type": "mapper_parsing_exception", "reason": "bad field"},
            }
        }
        for position in range(len(docs))
    ]
    return SimpleNamespace(body={"errors": True, "items": items})


def _repository(es_client: MagicMock) -> ArticleRepository:
    return ArticleRepository(cast(Elasticsearch, es_client), index="dictionary")


def _patch_runtime(monkeypatch: pytest.MonkeyPatch, es_client: MagicMock) -> None:
    """Point the importer's settings and client at test doubles."""
    monkeypatch.setattr(
        "scripts.import_dictionary.get_settings",
        lambda: Settings(es_index="test-index", ingestion_batch_size=2),
    )
    monkeypatch.setattr(
        "scripts.import_dictionary.get_elasticsearch_client",
        lambda: cast(Elasticsearch, es_client),
    )


def test_parser_accepts_multiple_files_and_recreate_flag() -> None:
    args = build_argument_parser().parse_args(["--recreate-index", "a.json", "b.json", "c.json"])

    assert args.files == ["a.json", "b.json", "c.json"]
    assert args.recreate_index is True


def test_parser_accepts_if_changed_flag() -> None:
    args = build_argument_parser().parse_args(["--if-changed", "a.json"])

    assert args.if_changed is True


def test_parser_defaults_recreate_index_to_false() -> None:
    args = build_argument_parser().parse_args(["a.json"])

    assert args.recreate_index is False


def test_parser_requires_at_least_one_file() -> None:
    with pytest.raises(SystemExit):
        build_argument_parser().parse_args([])


def test_validate_dictionary_file_accepts_valid_array(tmp_path: Path) -> None:
    path = _write_file(
        tmp_path / "valid.json",
        [_article_dict(word="першае слова"), _article_dict(word="другое слова")],
    )

    articles = validate_dictionary_file(path)

    assert [article.word for article in articles] == [
        "першае слова",
        "другое слова",
    ]
    assert all(isinstance(article, DictionaryArticle) for article in articles)


def test_validate_dictionary_file_rejects_invalid_json(tmp_path: Path) -> None:
    path = tmp_path / "broken.json"
    path.write_text("{not json", encoding="utf-8")

    with pytest.raises(DictionaryFileError, match="not valid JSON"):
        validate_dictionary_file(path)


def test_validate_dictionary_file_rejects_non_array_structure(tmp_path: Path) -> None:
    path = _write_file(tmp_path / "object.json", {"articles": [_article_dict()]})

    with pytest.raises(DictionaryFileError, match="JSON array"):
        validate_dictionary_file(path)


def test_validate_dictionary_file_reports_record_positions(tmp_path: Path) -> None:
    good = _article_dict()
    bad = _article_dict()
    del bad["raw"]
    path = _write_file(tmp_path / "mixed.json", [good, bad, good])

    with pytest.raises(DictionaryFileError, match="record 2"):
        validate_dictionary_file(path)


def test_validate_dictionary_file_rejects_unknown_fields(tmp_path: Path) -> None:
    record = _article_dict()
    record["unexpected"] = True
    path = _write_file(tmp_path / "strict.json", [record])

    with pytest.raises(DictionaryFileError):
        validate_dictionary_file(path)


def test_validate_dictionary_file_reports_all_invalid_records(
    tmp_path: Path,
) -> None:
    bad = _article_dict()
    del bad["word"]
    path = _write_file(tmp_path / "bad.json", [bad, bad])

    with pytest.raises(DictionaryFileError, match="2 invalid record"):
        validate_dictionary_file(path)


def test_validate_dictionary_file_accepts_empty_array(tmp_path: Path) -> None:
    path = _write_file(tmp_path / "empty.json", [])

    assert validate_dictionary_file(path) == []


def test_validate_dictionary_file_missing_file(tmp_path: Path) -> None:
    missing = tmp_path / "missing.json"

    with pytest.raises(DictionaryFileError, match="cannot read"):
        validate_dictionary_file(missing)


def test_dataset_fingerprint_is_order_independent_and_detects_changes(
    tmp_path: Path,
) -> None:
    first = _write_file(tmp_path / "a.json", [_article_dict(word="а")])
    second = _write_file(tmp_path / "b.json", [_article_dict(word="б")])

    original = dataset_fingerprint([first, second])

    assert dataset_fingerprint([second, first]) == original
    _write_file(second, [_article_dict(word="зменена")])
    assert dataset_fingerprint([first, second]) != original


def test_in_batches_groups_and_flushes_tail() -> None:
    articles = [_article(line=index + 1) for index in range(5)]

    batches = list(in_batches(articles, size=2))

    assert [len(batch) for batch in batches] == [2, 2, 1]
    assert batches[0][0].line == 1
    assert batches[2][0].line == 5


def test_in_batches_rejects_non_positive_size() -> None:
    with pytest.raises(ValueError):
        list(in_batches([], size=0))


def test_import_file_indexes_in_batches(es_client: MagicMock, tmp_path: Path) -> None:
    articles = [_article_dict(word=f"слова-{index}") for index in range(5)]
    path = _write_file(tmp_path / "data.json", articles)
    es_client.bulk.side_effect = _bulk_response_from_operations
    repository = _repository(es_client)

    result = import_file(repository, path, batch_size=2)

    assert result.records == 5
    assert result.indexed == 5
    assert result.failed == 0
    assert result.errors == ()
    assert es_client.bulk.call_count == 3
    operation_counts = [len(call.kwargs["operations"]) for call in es_client.bulk.call_args_list]
    assert operation_counts == [4, 4, 2]


def test_import_file_empty_file_skips_elasticsearch(es_client: MagicMock, tmp_path: Path) -> None:
    path = _write_file(tmp_path / "empty.json", [])
    repository = _repository(es_client)

    result = import_file(repository, path, batch_size=2)

    assert result.records == 0
    assert result.indexed == 0
    es_client.bulk.assert_not_called()


def test_import_file_invalid_file_raises_before_indexing(
    es_client: MagicMock, tmp_path: Path
) -> None:
    path = _write_file(tmp_path / "bad.json", [_article_dict(), {"word": "x"}])
    repository = _repository(es_client)

    with pytest.raises(DictionaryFileError):
        import_file(repository, path, batch_size=2)

    es_client.bulk.assert_not_called()


def test_import_file_reports_rejected_records(es_client: MagicMock, tmp_path: Path) -> None:
    path = _write_file(tmp_path / "data.json", [_article_dict(), _article_dict()])
    es_client.bulk.side_effect = _bulk_rejecting_response
    repository = _repository(es_client)

    result = import_file(repository, path, batch_size=2)

    assert result.records == 2
    assert result.indexed == 0
    assert result.failed == 2
    assert len(result.errors) == 2
    assert "mapper_parsing_exception" in result.errors[0]


def test_import_file_logs_progress(
    es_client: MagicMock, tmp_path: Path, caplog: pytest.LogCaptureFixture
) -> None:
    caplog.set_level("INFO")
    articles = [_article_dict(word=f"слова-{index}") for index in range(3)]
    path = _write_file(tmp_path / "data.json", articles)
    es_client.bulk.side_effect = _bulk_response_from_operations
    repository = _repository(es_client)

    import_file(repository, path, batch_size=2)

    assert "progress: indexed 2 of 3" in caplog.text
    assert "imported" in caplog.text
    assert caplog.text.count("3 record(s), 3 indexed, 0 rejected") == 1


def test_run_success_creates_index_and_indexes_records(
    monkeypatch: pytest.MonkeyPatch, es_client: MagicMock, tmp_path: Path
) -> None:
    _patch_runtime(monkeypatch, es_client)
    es_client.indices.exists.return_value = False
    es_client.bulk.side_effect = _bulk_response_from_operations
    files = [
        _write_file(tmp_path / "a.json", [_article_dict(word="слова-а")]),
        _write_file(tmp_path / "b.json", [_article_dict(word="слова-б")]),
    ]

    exit_code = run([str(files[0]), str(files[1])])

    assert exit_code == 0
    es_client.indices.create.assert_called_once()
    es_client.indices.delete.assert_not_called()
    assert es_client.bulk.call_count == 2


def test_run_does_not_recreate_existing_index(
    monkeypatch: pytest.MonkeyPatch, es_client: MagicMock, tmp_path: Path
) -> None:
    _patch_runtime(monkeypatch, es_client)
    es_client.indices.exists.return_value = True
    es_client.bulk.side_effect = _bulk_response_from_operations
    path = _write_file(tmp_path / "a.json", [_article_dict()])

    assert run([str(path)]) == 0
    es_client.indices.delete.assert_not_called()
    es_client.indices.create.assert_not_called()


def test_run_if_changed_skips_matching_populated_dataset(
    monkeypatch: pytest.MonkeyPatch, es_client: MagicMock, tmp_path: Path
) -> None:
    _patch_runtime(monkeypatch, es_client)
    es_client.indices.exists.return_value = True
    es_client.count.return_value = SimpleNamespace(body={"count": 1})
    path = _write_file(tmp_path / "a.json", [_article_dict()])
    fingerprint = dataset_fingerprint([path])
    es_client.indices.get_mapping.return_value = SimpleNamespace(
        body={"test-index": {"mappings": {"_meta": {"dataset_sha256": fingerprint}}}}
    )

    assert run(["--if-changed", str(path)]) == 0
    es_client.bulk.assert_not_called()
    es_client.indices.put_mapping.assert_not_called()


def test_run_if_changed_imports_and_records_new_fingerprint(
    monkeypatch: pytest.MonkeyPatch, es_client: MagicMock, tmp_path: Path
) -> None:
    _patch_runtime(monkeypatch, es_client)
    es_client.indices.exists.return_value = True
    es_client.count.return_value = SimpleNamespace(body={"count": 1})
    es_client.indices.get_mapping.return_value = SimpleNamespace(
        body={"test-index": {"mappings": {"_meta": {"dataset_sha256": "old"}}}}
    )
    es_client.bulk.side_effect = _bulk_response_from_operations
    path = _write_file(tmp_path / "a.json", [_article_dict()])

    assert run(["--if-changed", str(path)]) == 0
    es_client.indices.delete.assert_called_once_with(index="test-index")
    es_client.indices.create.assert_called_once()
    es_client.indices.put_mapping.assert_called_once_with(
        index="test-index",
        meta={"dataset_sha256": dataset_fingerprint([path])},
    )


def test_run_if_changed_keeps_existing_index_when_new_data_is_invalid(
    monkeypatch: pytest.MonkeyPatch, es_client: MagicMock, tmp_path: Path
) -> None:
    _patch_runtime(monkeypatch, es_client)
    es_client.indices.exists.return_value = True
    es_client.count.return_value = SimpleNamespace(body={"count": 1})
    es_client.indices.get_mapping.return_value = SimpleNamespace(
        body={"test-index": {"mappings": {"_meta": {"dataset_sha256": "old"}}}}
    )
    path = _write_file(tmp_path / "bad.json", [{"word": "missing fields"}])

    assert run(["--if-changed", str(path)]) == 1
    es_client.indices.delete.assert_not_called()
    es_client.bulk.assert_not_called()


def test_run_recreate_index_deletes_then_creates(
    monkeypatch: pytest.MonkeyPatch, es_client: MagicMock, tmp_path: Path
) -> None:
    _patch_runtime(monkeypatch, es_client)
    es_client.indices.exists.return_value = True
    es_client.bulk.side_effect = _bulk_response_from_operations
    path = _write_file(tmp_path / "a.json", [_article_dict()])

    assert run(["--recreate-index", str(path)]) == 0
    es_client.indices.delete.assert_called_once()
    es_client.indices.create.assert_called_once()


def test_run_bulk_indexes_in_settings_batch_size(
    monkeypatch: pytest.MonkeyPatch, es_client: MagicMock, tmp_path: Path
) -> None:
    monkeypatch.setattr(
        "scripts.import_dictionary.get_settings",
        lambda: Settings(es_index="test-index", ingestion_batch_size=3),
    )
    monkeypatch.setattr(
        "scripts.import_dictionary.get_elasticsearch_client",
        lambda: cast(Elasticsearch, es_client),
    )
    es_client.indices.exists.return_value = False
    es_client.bulk.side_effect = _bulk_response_from_operations
    articles = [_article_dict(word=f"слова-{index}") for index in range(7)]
    path = _write_file(tmp_path / "data.json", articles)

    assert run([str(path)]) == 0
    assert es_client.bulk.call_count == 3
    operation_counts = [len(call.kwargs["operations"]) for call in es_client.bulk.call_args_list]
    assert operation_counts == [6, 6, 2]


def test_run_fails_nonzero_on_invalid_file(
    monkeypatch: pytest.MonkeyPatch, es_client: MagicMock, tmp_path: Path
) -> None:
    _patch_runtime(monkeypatch, es_client)
    es_client.indices.exists.return_value = False
    es_client.bulk.side_effect = _bulk_response_from_operations
    path = _write_file(tmp_path / "bad.json", [{"word": "не хапае raw"}])

    exit_code = run([str(path)])

    assert exit_code == 1
    es_client.bulk.assert_not_called()


def test_run_fails_nonzero_when_index_preparation_fails(
    monkeypatch: pytest.MonkeyPatch, es_client: MagicMock, tmp_path: Path
) -> None:
    _patch_runtime(monkeypatch, es_client)
    es_client.indices.exists.side_effect = RuntimeError("cluster unreachable")
    path = _write_file(tmp_path / "a.json", [_article_dict()])

    assert run([str(path)]) == 1
    es_client.bulk.assert_not_called()


def test_run_continues_after_failed_file(
    monkeypatch: pytest.MonkeyPatch, es_client: MagicMock, tmp_path: Path
) -> None:
    _patch_runtime(monkeypatch, es_client)
    es_client.indices.exists.return_value = False
    es_client.bulk.side_effect = _bulk_response_from_operations
    bad = _write_file(tmp_path / "bad.json", [{"line": 1}])
    good = _write_file(tmp_path / "good.json", [_article_dict(word="слова-добрае")])

    exit_code = run([str(bad), str(good)])

    assert exit_code == 1
    assert es_client.bulk.call_count == 1  # only the good file was indexed


def test_run_fails_nonzero_when_records_are_rejected(
    monkeypatch: pytest.MonkeyPatch, es_client: MagicMock, tmp_path: Path
) -> None:
    _patch_runtime(monkeypatch, es_client)
    es_client.indices.exists.return_value = False
    es_client.bulk.side_effect = _bulk_rejecting_response
    path = _write_file(tmp_path / "a.json", [_article_dict()])

    assert run([str(path)]) == 1


def test_main_returns_exit_code(
    monkeypatch: pytest.MonkeyPatch, es_client: MagicMock, tmp_path: Path
) -> None:
    _patch_runtime(monkeypatch, es_client)
    es_client.indices.exists.return_value = False
    es_client.bulk.side_effect = _bulk_response_from_operations
    path = _write_file(tmp_path / "a.json", [_article_dict()])

    assert main([str(path)]) == 0
