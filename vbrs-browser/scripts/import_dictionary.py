"""Command-line importer for dictionary JSON files.

Reads one or more dictionary data files (JSON arrays of article objects),
validates every record against :class:`backend.models.dictionary.DictionaryArticle`
and bulk-indexes the records into Elasticsearch::

    python -m scripts.import_dictionary data-1.json data-2.json [--recreate-index]

Behavior:

* Files are processed one at a time; only the file currently being imported
  is held in memory.
* Each file is validated in full before anything from it is indexed, so a
  file containing any invalid record is rejected as a whole.
* The index is created with the explicit mapping (see
  :mod:`backend.elasticsearch.mappings`) when it does not exist yet. It is
  recreated when ``--recreate-index`` is passed, or when ``--if-changed``
  detects a different source dataset.
* Records are indexed through
  :class:`backend.repositories.articles.ArticleRepository` in batches of
  ``ingestion_batch_size`` (from settings), with progress logged after every
  batch.
* Any failure (invalid input, unreachable cluster, documents rejected by
  Elasticsearch) makes the process exit with a non-zero status.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import logging
import sys
from collections.abc import Iterable, Iterator, Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path

from elasticsearch import Elasticsearch
from pydantic import ValidationError

from backend.config.settings import get_settings
from backend.elasticsearch.client import get_elasticsearch_client
from backend.elasticsearch.mappings import (
    INDEX_MAPPING,
    INDEX_SETTINGS,
    create_index_if_missing,
    recreate_index,
)
from backend.models.dictionary import DictionaryArticle
from backend.repositories.articles import ArticleRepository

logger = logging.getLogger(__name__)

#: Maximum number of per-record rejection details logged for one file.
_MAX_REPORTED_ERRORS = 20
_DATASET_FINGERPRINT_KEY = "dataset_sha256"


class DictionaryFileError(ValueError):
    """Raised when a dictionary data file cannot be read, parsed or validated."""


@dataclass(frozen=True, slots=True)
class FileImportResult:
    path: Path
    records: int
    indexed: int
    failed: int
    errors: tuple[str, ...]


def build_argument_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="python -m scripts.import_dictionary",
        description=(
            "Import dictionary JSON files into Elasticsearch. Each file must "
            "contain a JSON array of dictionary article objects."
        ),
    )
    parser.add_argument(
        "--recreate-index",
        action="store_true",
        help="delete and recreate the index with the explicit mapping before importing",
    )
    parser.add_argument(
        "--if-changed",
        action="store_true",
        help=(
            "skip importing when this exact dataset is already indexed; "
            "recreate the index before importing when it changed"
        ),
    )
    parser.add_argument(
        "files",
        nargs="+",
        metavar="FILE",
        help="dictionary data file to import (JSON array of articles); "
        "multiple files are processed one at a time",
    )
    return parser


def dataset_fingerprint(paths: Iterable[Path]) -> str:
    """Return a stable SHA-256 fingerprint for the data and index schema."""
    digest = hashlib.sha256()
    digest.update(
        json.dumps(
            {"mapping": INDEX_MAPPING, "settings": INDEX_SETTINGS},
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        ).encode()
    )
    for path in sorted(paths, key=lambda item: item.name):
        try:
            with path.open("rb") as handle:
                file_digest = hashlib.file_digest(handle, "sha256").digest()
        except OSError as exc:
            raise DictionaryFileError(f"cannot read '{path}': {exc}") from exc
        name = path.name.encode()
        digest.update(len(name).to_bytes(4, "big"))
        digest.update(name)
        digest.update(file_digest)
    return digest.hexdigest()


def dataset_is_current(client: Elasticsearch, index: str, fingerprint: str) -> bool:
    """Return whether a populated index records ``fingerprint`` as imported."""
    count_body = client.count(index=index).body
    if count_body.get("count") == 0:
        return False

    mapping_body = client.indices.get_mapping(index=index).body
    index_mapping = mapping_body.get(index)
    if not isinstance(index_mapping, Mapping):
        return False
    mappings = index_mapping.get("mappings")
    if not isinstance(mappings, Mapping):
        return False
    metadata = mappings.get("_meta")
    return isinstance(metadata, Mapping) and metadata.get(_DATASET_FINGERPRINT_KEY) == fingerprint


def validate_dictionary_file(path: Path) -> list[DictionaryArticle]:
    """Load ``path`` and validate it as an array of dictionary articles.

    The file must contain a single JSON array whose elements are valid
    :class:`DictionaryArticle` records. All validation errors are collected,
    so a file with several bad records reports every one of them (with its
    position) in a single :class:`DictionaryFileError`.

    Raises:
        DictionaryFileError: When the file cannot be read, is not valid JSON,
            is not a JSON array, or contains any invalid record.
    """
    try:
        with path.open("r", encoding="utf-8") as handle:
            raw = json.load(handle)
    except OSError as exc:
        raise DictionaryFileError(f"cannot read '{path}': {exc}") from exc
    except UnicodeError as exc:
        raise DictionaryFileError(f"'{path}' is not valid UTF-8 text: {exc}") from exc
    except json.JSONDecodeError as exc:
        raise DictionaryFileError(f"'{path}' is not valid JSON: {exc}") from exc

    if not isinstance(raw, list):
        raise DictionaryFileError(
            f"'{path}' must contain a JSON array of dictionary articles, got {type(raw).__name__}"
        )

    articles: list[DictionaryArticle] = []
    invalid: list[str] = []
    for position, raw_record in enumerate(raw, start=1):
        try:
            articles.append(DictionaryArticle.model_validate(raw_record))
        except ValidationError as exc:
            invalid.append(f"record {position}: {_format_validation_errors(exc)}")

    if invalid:
        details = "\n".join(f"  - {message}" for message in invalid)
        raise DictionaryFileError(f"'{path}' contains {len(invalid)} invalid record(s):\n{details}")
    return articles


def _format_validation_errors(exc: ValidationError) -> str:
    details: list[str] = []
    for error in exc.errors(include_url=False):
        location = ".".join(str(part) for part in error["loc"]) or "<record>"
        details.append(f"{location}: {error['msg']}")
    return "; ".join(details)


def in_batches(items: Iterable[DictionaryArticle], size: int) -> Iterator[list[DictionaryArticle]]:
    if size < 1:
        raise ValueError("batch size must be positive")
    batch: list[DictionaryArticle] = []
    for item in items:
        batch.append(item)
        if len(batch) >= size:
            yield batch
            batch = []
    if batch:
        yield batch


def import_file(repository: ArticleRepository, path: Path, *, batch_size: int) -> FileImportResult:
    """Validate ``path`` and index every record in batches of ``batch_size``.

    Validation happens before indexing: if any record in the file is invalid,
    :class:`DictionaryFileError` is raised and nothing from the file is
    indexed. Progress is logged after every batch.
    """
    articles = validate_dictionary_file(path)
    if not articles:
        logger.warning("'%s' contains no records; nothing to index", path)
        return FileImportResult(path=path, records=0, indexed=0, failed=0, errors=())

    indexed_total = 0
    failed_total = 0
    errors: list[str] = []
    processed = 0
    for batch in in_batches(articles, batch_size):
        result = repository.bulk_index(batch, batch_size=batch_size)
        indexed_total += result.indexed
        failed_total += result.failed
        errors.extend(result.errors)
        processed += len(batch)
        logger.info(
            "progress: indexed %d of %d record(s) from '%s' (%d rejected)",
            processed,
            len(articles),
            path,
            failed_total,
        )

    logger.info(
        "imported '%s': %d record(s), %d indexed, %d rejected",
        path,
        len(articles),
        indexed_total,
        failed_total,
    )
    return FileImportResult(
        path=path,
        records=len(articles),
        indexed=indexed_total,
        failed=failed_total,
        errors=tuple(errors),
    )


def run(argv: Sequence[str] | None = None) -> int:
    """Run the importer end to end and return the process exit code.

    The index name, batch size and Elasticsearch URL all come from the shared
    pydantic-settings configuration (see :mod:`backend.config.settings`). Files
    are processed one at a time; a failing file is reported and the remaining
    files are still attempted. Returns a non-zero code when anything failed.
    """
    args = build_argument_parser().parse_args(argv)
    paths = [Path(path_string) for path_string in args.files]
    settings = get_settings()
    index = settings.es_index
    batch_size = settings.ingestion_batch_size
    fingerprint: str | None = None

    if args.if_changed:
        try:
            fingerprint = dataset_fingerprint(paths)
        except DictionaryFileError as exc:
            logger.error("unable to fingerprint dictionary dataset: %s", exc)
            return 1

    client = get_elasticsearch_client()
    try:
        fresh_index = False
        if args.recreate_index:
            recreate_index(client, index)
            fresh_index = True
            logger.info("recreated index '%s'", index)
        elif create_index_if_missing(client, index):
            fresh_index = True
            logger.info("created index '%s'", index)
        else:
            logger.info("index '%s' already exists", index)

        if fingerprint is not None and not fresh_index:
            if dataset_is_current(client, index, fingerprint):
                logger.info("dictionary dataset is unchanged; skipping import")
                return 0
            try:
                for path in paths:
                    validate_dictionary_file(path)
            except DictionaryFileError as exc:
                logger.error(
                    "changed dictionary dataset is invalid; existing index kept: %s",
                    exc,
                )
                return 1
            recreate_index(client, index)
            logger.info("dictionary dataset changed; recreated index '%s'", index)
    except Exception as exc:
        logger.exception("unable to prepare Elasticsearch index '%s': %s", index, exc)
        return 1

    repository = ArticleRepository(client=client, index=index)

    ok_files = 0
    failed_files = 0
    records = 0
    indexed = 0
    rejected = 0

    for path in paths:
        try:
            result = import_file(repository, path, batch_size=batch_size)
        except DictionaryFileError as exc:
            failed_files += 1
            logger.error("'%s' was not imported: %s", path, exc)
            continue
        except Exception as exc:
            failed_files += 1
            logger.exception("'%s' failed unexpectedly: %s", path, exc)
            continue

        records += result.records
        indexed += result.indexed
        rejected += result.failed
        if result.failed:
            failed_files += 1
            logger.error("'%s': %d record(s) were rejected by Elasticsearch", path, result.failed)
            for message in result.errors[:_MAX_REPORTED_ERRORS]:
                logger.error("  %s", message)
            if len(result.errors) > _MAX_REPORTED_ERRORS:
                logger.error(
                    "  ... and %d more error(s)",
                    len(result.errors) - _MAX_REPORTED_ERRORS,
                )
        else:
            ok_files += 1

    if failed_files:
        logger.error(
            "import failed: %d file(s) imported cleanly, %d file(s) had errors "
            "(%d record(s) read, %d indexed, %d rejected)",
            ok_files,
            failed_files,
            records,
            indexed,
            rejected,
        )
        return 1

    if fingerprint is not None:
        try:
            client.indices.put_mapping(index=index, meta={_DATASET_FINGERPRINT_KEY: fingerprint})
        except Exception as exc:
            logger.exception("unable to record dictionary dataset fingerprint: %s", exc)
            return 1

    logger.info(
        "import complete: %d file(s), %d record(s) read, %d indexed, %d rejected",
        ok_files,
        records,
        indexed,
        rejected,
    )
    return 0


def main(argv: Sequence[str] | None = None) -> int:
    settings = get_settings()
    logging.basicConfig(
        level=settings.log_level.value,
        format="%(levelname)s %(message)s",
    )
    return run(argv)


if __name__ == "__main__":
    sys.exit(main())
