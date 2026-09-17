"""Tests for the explicit Elasticsearch index mapping and creation helpers."""

from __future__ import annotations

from collections.abc import Mapping
from typing import cast
from unittest.mock import MagicMock

import pytest
from elastic_transport import ApiResponseMeta, HttpHeaders, NodeConfig
from elasticsearch import Elasticsearch
from elasticsearch.exceptions import BadRequestError

from api.elasticsearch.mappings import (
    INDEX_MAPPING,
    INDEX_SETTINGS,
    create_index_if_missing,
    recreate_index,
)

REQUIRED_PROPERTIES = {
    "word",
    "latin",
    "raw",
    "definitions",
    "gender",
    "is_plural",
    "is_proper",
    "be_notes",
    "ru_notes",
    "sources",
    "is_link",
}


def _properties() -> Mapping[str, object]:
    properties = INDEX_MAPPING.get("properties")
    assert isinstance(properties, Mapping)
    return properties


def _api_meta(status: int) -> ApiResponseMeta:
    return ApiResponseMeta(
        status=status,
        http_version="1.1",
        headers=HttpHeaders({}),
        duration=0.001,
        node=NodeConfig(scheme="http", host="localhost", port=9200),
    )


def test_mapping_defines_all_required_fields() -> None:
    assert set(_properties()) >= REQUIRED_PROPERTIES


def test_mapping_is_dynamic_strict() -> None:
    assert INDEX_MAPPING.get("dynamic") == "strict"


def test_free_text_fields_use_case_insensitive_text_analyzer() -> None:
    for field in ("word", "latin", "raw"):
        definition = _properties().get(field)
        assert isinstance(definition, Mapping)
        assert definition.get("type") == "text"
        assert definition.get("analyzer") == "text_analyzer"


def test_definitions_text_is_searchable() -> None:
    definitions = _properties().get("definitions")
    assert isinstance(definitions, Mapping)

    subproperties = definitions.get("properties")
    assert isinstance(subproperties, Mapping)

    text = subproperties.get("text")
    assert isinstance(text, Mapping)
    assert text.get("type") == "text"
    assert text.get("analyzer") == "text_analyzer"


def test_boolean_and_keyword_fields_are_mapped() -> None:
    for field in ("is_plural", "is_proper", "is_link"):
        definition = _properties().get(field)
        assert isinstance(definition, Mapping)
        assert definition.get("type") == "boolean"

    for field in ("gender", "sources"):
        definition = _properties().get(field)
        assert isinstance(definition, Mapping)
        assert definition.get("type") == "keyword"


def test_analyzer_is_defined_with_lowercase_filter() -> None:
    index = INDEX_SETTINGS.get("index")
    assert isinstance(index, Mapping)

    analysis = index.get("analysis")
    assert isinstance(analysis, Mapping)

    analyzers = analysis.get("analyzer")
    assert isinstance(analyzers, Mapping)

    text_analyzer = analyzers.get("text_analyzer")
    assert isinstance(text_analyzer, Mapping)
    assert text_analyzer.get("type") == "custom"
    assert text_analyzer.get("filter") == ["lowercase"]


def test_create_index_if_missing_creates_when_absent(es_client: MagicMock) -> None:
    es_client.indices.exists.return_value = False

    created = create_index_if_missing(cast(Elasticsearch, es_client), "dictionary")

    assert created is True
    es_client.indices.create.assert_called_once_with(
        index="dictionary", settings=INDEX_SETTINGS, mappings=INDEX_MAPPING
    )


def test_create_index_if_missing_skips_when_present(es_client: MagicMock) -> None:
    es_client.indices.exists.return_value = True

    assert create_index_if_missing(cast(Elasticsearch, es_client), "dictionary") is False
    es_client.indices.create.assert_not_called()


def test_create_index_if_missing_tolerates_create_race(es_client: MagicMock) -> None:
    es_client.indices.exists.return_value = False
    es_client.indices.create.side_effect = BadRequestError(
        "index exists",
        _api_meta(400),
        {"error": {"type": "resource_already_exists_exception"}},
    )

    assert create_index_if_missing(cast(Elasticsearch, es_client), "dictionary") is False


def test_create_index_if_missing_propagates_other_failures(
    es_client: MagicMock,
) -> None:
    es_client.indices.exists.return_value = False
    es_client.indices.create.side_effect = BadRequestError(
        "invalid mapping",
        _api_meta(400),
        {"error": {"type": "illegal_argument_exception"}},
    )

    with pytest.raises(BadRequestError):
        create_index_if_missing(cast(Elasticsearch, es_client), "dictionary")


def test_recreate_index_deletes_then_creates(es_client: MagicMock) -> None:
    es_client.indices.exists.return_value = True

    recreate_index(cast(Elasticsearch, es_client), "dictionary")

    es_client.indices.delete.assert_called_once_with(index="dictionary")
    es_client.indices.create.assert_called_once_with(
        index="dictionary", settings=INDEX_SETTINGS, mappings=INDEX_MAPPING
    )


def test_recreate_index_creates_when_missing(es_client: MagicMock) -> None:
    es_client.indices.exists.return_value = False

    recreate_index(cast(Elasticsearch, es_client), "dictionary")

    es_client.indices.delete.assert_not_called()
    es_client.indices.create.assert_called_once()