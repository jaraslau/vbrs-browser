from __future__ import annotations

import pytest
from pydantic import ValidationError

from backend.config.settings import LogLevel, Settings, get_settings


def test_defaults() -> None:
    settings = Settings(_env_file=None)
    assert settings.backend_host == "0.0.0.0"
    assert settings.backend_port == 8000
    assert settings.cors_origins == ["http://localhost:5173", "http://localhost:8080"]
    assert settings.es_url == "http://localhost:9200"
    assert settings.es_index == "dictionary"
    assert settings.es_connect_timeout == 5.0
    assert settings.es_request_timeout == 30.0
    assert settings.es_pit_keep_alive_seconds == 60
    assert settings.page_size == 20
    assert settings.max_page_size == 100
    assert settings.ingestion_batch_size == 1000
    assert settings.log_level is LogLevel.INFO
    assert settings.api_v1_prefix == "/api/v1"


def test_get_settings_is_cached() -> None:
    assert get_settings() is get_settings()


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
    monkeypatch.setenv("CORS_ORIGINS", '["http://localhost:3000", "http://localhost:8080"]')

    settings = Settings(_env_file=None)

    assert settings.cors_origins == ["http://localhost:3000", "http://localhost:8080"]


def test_page_size_must_not_exceed_max_page_size() -> None:
    with pytest.raises(ValidationError):
        Settings(_env_file=None, page_size=200, max_page_size=100)


def test_backend_port_must_be_in_valid_range() -> None:
    with pytest.raises(ValidationError):
        Settings(_env_file=None, backend_port=0)
    with pytest.raises(ValidationError):
        Settings(_env_file=None, backend_port=65536)


def test_page_size_must_be_positive() -> None:
    with pytest.raises(ValidationError):
        Settings(_env_file=None, page_size=0)


def test_elasticsearch_timeouts_must_be_positive() -> None:
    with pytest.raises(ValidationError):
        Settings(_env_file=None, es_connect_timeout=0)
    with pytest.raises(ValidationError):
        Settings(_env_file=None, es_request_timeout=-1)
    with pytest.raises(ValidationError):
        Settings(_env_file=None, es_pit_keep_alive_seconds=0)


def test_page_size_cannot_exceed_elasticsearch_result_window() -> None:
    with pytest.raises(ValidationError):
        Settings(_env_file=None, max_page_size=10_001)


def test_log_level_must_be_a_known_value() -> None:
    with pytest.raises(ValidationError):
        Settings(_env_file=None, log_level="VERBOSE")


def test_api_prefix_must_be_well_formed() -> None:
    with pytest.raises(ValidationError):
        Settings(_env_file=None, api_v1_prefix="api/v1/")
