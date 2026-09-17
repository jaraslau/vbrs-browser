"""Tests for the pydantic-settings based configuration module."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from api.config.settings import LogLevel, Settings


def test_defaults() -> None:
    settings = Settings(_env_file=None)
    assert settings.backend_host == "0.0.0.0"
    assert settings.backend_port == 8000
    assert settings.es_url == "http://localhost:9200"
    assert settings.es_index == "dictionary"
    assert settings.page_size == 20
    assert settings.max_page_size == 100
    assert settings.ingestion_batch_size == 1000
    assert settings.log_level is LogLevel.INFO
    assert settings.api_v1_prefix == "/api/v1"


def test_environment_variables_override_defaults(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("BACKEND_PORT", "9000")
    monkeypatch.setenv("ES_URL", "http://elasticsearch.internal:9200")
    monkeypatch.setenv("ES_INDEX", "custom_dictionary")
    monkeypatch.setenv("PAGE_SIZE", "50")
    monkeypatch.setenv("LOG_LEVEL", "DEBUG")

    settings = Settings(_env_file=None)

    assert settings.backend_port == 9000
    assert settings.es_url == "http://elasticsearch.internal:9200"
    assert settings.es_index == "custom_dictionary"
    assert settings.page_size == 50
    assert settings.log_level is LogLevel.DEBUG


def test_cors_origins_parsed_from_json_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv(
        "CORS_ORIGINS", '["http://localhost:3000", "http://localhost:8080"]'
    )

    settings = Settings(_env_file=None)

    assert settings.cors_origins == ["http://localhost:3000", "http://localhost:8080"]


def test_page_size_must_not_exceed_max_page_size() -> None:
    with pytest.raises(ValidationError):
        Settings(_env_file=None, page_size=200, max_page_size=100)


def test_api_prefix_must_be_well_formed() -> None:
    with pytest.raises(ValidationError):
        Settings(_env_file=None, api_v1_prefix="api/v1/")