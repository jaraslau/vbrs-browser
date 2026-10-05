from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from backend.main import create_app


def _get_health(client: TestClient) -> tuple[int, dict[str, str]]:
    with client:
        response = client.get("/api/v1/health")
    return response.status_code, response.json()


def test_health_reports_connected_when_ping_succeeds(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr("backend.services.health.ping_elasticsearch", lambda: True)

    status_code, body = _get_health(TestClient(create_app()))

    assert status_code == 200
    assert body == {"status": "ok", "elasticsearch": "connected"}


def test_health_reports_unavailable_when_ping_fails(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr("backend.services.health.ping_elasticsearch", lambda: False)

    status_code, body = _get_health(TestClient(create_app()))

    assert status_code == 200
    assert body == {"status": "ok", "elasticsearch": "unavailable"}


def test_health_reports_unavailable_when_ping_raises(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def failing_ping() -> bool:
        raise ConnectionError("connection refused")

    monkeypatch.setattr("backend.services.health.ping_elasticsearch", failing_ping)

    status_code, body = _get_health(TestClient(create_app()))

    assert status_code == 200
    assert body == {"status": "ok", "elasticsearch": "unavailable"}
