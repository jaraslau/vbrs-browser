from __future__ import annotations

from elastic_transport import ApiResponseMeta, HttpHeaders, NodeConfig
from elasticsearch import (
    BadRequestError,
    ConnectionError as EsConnectionError,
    ConnectionTimeout,
    NotFoundError,
    TransportError,
)
from fastapi import HTTPException
from fastapi.testclient import TestClient

from backend.main import create_app
from backend.repositories.articles import RepositoryResponseError
from backend.services.articles import ArticleNotFoundError


def _meta(status: int) -> ApiResponseMeta:
    """Build the response metadata every Elasticsearch exception carries."""
    return ApiResponseMeta(
        status=status,
        http_version="1.1",
        headers=HttpHeaders({}),
        duration=0.001,
        node=NodeConfig(scheme="http", host="localhost", port=9200),
    )


def test_http_exception_keeps_the_json_detail_shape() -> None:
    app = create_app()

    @app.get("/boom")
    def boom() -> None:
        raise HTTPException(status_code=403, detail="forbidden")

    with TestClient(app) as client:
        response = client.get("/boom")

    assert response.status_code == 403
    assert response.json() == {"detail": "forbidden"}


def test_missing_article_maps_to_404() -> None:
    app = create_app()

    @app.get("/boom")
    def boom() -> None:
        raise ArticleNotFoundError("abc123")

    with TestClient(app) as client:
        response = client.get("/boom")

    assert response.status_code == 404
    assert response.json() == {"detail": "Article 'abc123' not found"}


def test_es_api_error_maps_to_502() -> None:
    app = create_app()

    @app.get("/boom")
    def boom() -> None:
        raise BadRequestError("bad request", _meta(400), {"error": {}})

    with TestClient(app) as client:
        response = client.get("/boom")

    assert response.status_code == 502
    assert response.json() == {"detail": "The search backend returned an error."}


def test_es_transport_error_maps_to_502() -> None:
    app = create_app()

    @app.get("/boom")
    def boom() -> None:
        raise TransportError("connection reset")

    with TestClient(app) as client:
        response = client.get("/boom")

    assert response.status_code == 502
    assert response.json() == {"detail": "The search backend returned an error."}


def test_es_connection_error_maps_to_503() -> None:
    app = create_app()

    @app.get("/boom")
    def boom() -> None:
        raise EsConnectionError("connection refused")

    with TestClient(app) as client:
        response = client.get("/boom")

    assert response.status_code == 503
    assert response.json() == {"detail": "The search backend is temporarily unavailable."}


def test_es_timeout_maps_to_503() -> None:
    app = create_app()

    @app.get("/boom")
    def boom() -> None:
        raise ConnectionTimeout("timed out")

    with TestClient(app) as client:
        response = client.get("/boom")

    assert response.status_code == 503
    assert response.json() == {"detail": "The search backend is temporarily unavailable."}


def test_es_missing_index_maps_to_503() -> None:
    app = create_app()

    @app.get("/boom")
    def boom() -> None:
        raise NotFoundError("index not found", _meta(404), {"error": {}})

    with TestClient(app) as client:
        response = client.get("/boom")

    assert response.status_code == 503


def test_repository_error_maps_to_500_without_leaking_details() -> None:
    app = create_app()

    @app.get("/boom")
    def boom() -> None:
        raise RepositoryResponseError("search response is missing the 'hits' object: {...}")

    with TestClient(app) as client:
        response = client.get("/boom")

    assert response.status_code == 500
    assert response.json() == {"detail": "The search backend returned an unexpected response."}


def test_unhandled_exception_maps_to_500_without_leaking_details() -> None:
    app = create_app()

    @app.get("/boom")
    def boom() -> None:
        raise RuntimeError("secret internal detail")

    with TestClient(app, raise_server_exceptions=False) as client:
        response = client.get("/boom")

    assert response.status_code == 500
    assert response.json() == {"detail": "An internal error occurred."}
    assert "secret" not in response.text


def test_unknown_path_returns_json_404() -> None:
    with TestClient(create_app()) as client:
        response = client.get("/api/v1/does-not-exist")

    assert response.status_code == 404
    assert response.json() == {"detail": "Not Found"}
