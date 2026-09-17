from __future__ import annotations

from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient

from api.main import create_app


def test_openapi_docs_are_enabled() -> None:
    with TestClient(create_app()) as client:
        docs = client.get("/docs")
        schema = client.get("/openapi.json")

    assert docs.status_code == 200
    assert schema.status_code == 200
    body = schema.json()
    assert body["info"]["title"] == "vbrs-browser API"
    assert set(body["paths"]) == {
        "/api/v1/health",
        "/api/v1/articles",
        "/api/v1/articles/{article_id}",
    }


def test_openapi_documents_query_parameters_and_responses() -> None:
    with TestClient(create_app()) as client:
        body = client.get("/openapi.json").json()

    article_params = body["paths"]["/api/v1/articles"]["get"]["parameters"]
    assert {param["name"] for param in article_params} == {"q", "page", "page_size"}

    article_responses = body["paths"]["/api/v1/articles/{article_id}"]["get"]["responses"]
    assert "404" in article_responses


def test_cors_allows_configured_origin(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("api.services.health.ping_elasticsearch", lambda: True)

    with TestClient(create_app()) as client:
        response = client.get("/api/v1/health", headers={"Origin": "http://localhost:5173"})

    assert response.headers.get("access-control-allow-origin") == "http://localhost:5173"


def test_cors_rejects_unconfigured_origin(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("api.services.health.ping_elasticsearch", lambda: True)

    with TestClient(create_app()) as client:
        response = client.get("/api/v1/health", headers={"Origin": "http://evil.example"})

    assert response.headers.get("access-control-allow-origin") is None


def test_lifespan_closes_the_elasticsearch_client(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    es_client = MagicMock()
    get_client = MagicMock(return_value=es_client)
    get_client.cache_clear = MagicMock()
    monkeypatch.setattr("api.main.get_elasticsearch_client", get_client)
    monkeypatch.setattr("api.services.health.ping_elasticsearch", lambda: True)

    with TestClient(create_app()) as client:
        client.get("/api/v1/health")

    get_client.assert_called_once()
    es_client.close.assert_called_once()
    get_client.cache_clear.assert_called_once()
