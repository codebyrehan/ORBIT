from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient

from orbit.api.server import create_app
from orbit.core.app import OrbitApp
from orbit.core.config import OrbitConfig


def test_health_readiness_and_metrics_are_exposed(tmp_path: Path) -> None:
    app = OrbitApp(OrbitConfig(data_dir=tmp_path / ".orbit"))
    api = create_app(app)
    with TestClient(api) as client:
        health = client.get("/health")
        ready = client.get("/ready")
        metrics = client.get("/v1/metrics")

    assert health.status_code == 200
    assert health.json()["status"] == "ok"
    assert ready.status_code == 200
    assert ready.json() == {"ready": True}
    assert metrics.status_code == 200
    assert metrics.json()["requests_total"] >= 0


def test_request_id_is_returned_and_audit_event_is_created(tmp_path: Path) -> None:
    app = OrbitApp(OrbitConfig(data_dir=tmp_path / ".orbit"))
    api = create_app(app)
    with TestClient(api) as client:
        response = client.get("/health", headers={"x-request-id": "production-readiness"})
        events = client.get("/v1/audit/events")

    assert response.status_code == 200
    assert response.headers["x-request-id"] == "production-readiness"
    assert events.status_code == 200
    assert any(item["request_id"] == "production-readiness" for item in events.json()["data"])
