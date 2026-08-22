from __future__ import annotations

from fastapi.testclient import TestClient

from orbit.api.production import app


def test_public_root_returns_service_metadata() -> None:
    response = TestClient(app).get("/")

    assert response.status_code == 200
    payload = response.json()
    assert payload["service"] == "ORBIT API"
    assert payload["status"] == "ok"
    assert payload["docs"] == "/docs"
    assert payload["health"] == "/health"
