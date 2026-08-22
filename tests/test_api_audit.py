from pathlib import Path

from fastapi.testclient import TestClient

from orbit.api.server import create_app
from orbit.core.app import OrbitApp
from orbit.core.config import OrbitConfig


def test_api_persists_audit_events_without_request_body(tmp_path: Path) -> None:
    app = OrbitApp(OrbitConfig(data_dir=tmp_path / ".orbit"))
    client = TestClient(create_app(app))

    response = client.get("/health", headers={"x-request-id": "audit-health"})
    assert response.status_code == 200

    events = client.get("/v1/audit/events?limit=10")
    assert events.status_code == 200
    matching = [event for event in events.json()["data"] if event["request_id"] == "audit-health"]
    assert matching
    assert matching[-1]["method"] == "GET"
    assert matching[-1]["path"] == "/health"
    assert matching[-1]["status_code"] == 200
    assert matching[-1]["authenticated"] is True


def test_api_audit_records_rejected_auth_without_secret(tmp_path: Path) -> None:
    app = OrbitApp(OrbitConfig(data_dir=tmp_path / ".orbit"))
    app.config = OrbitConfig(data_dir=tmp_path / ".orbit", api_key="super-secret")
    client = TestClient(create_app(app))

    response = client.get("/v1/system", headers={"x-request-id": "audit-auth"})
    assert response.status_code == 401

    events = client.get("/v1/audit/events?limit=10", headers={"authorization": "Bearer super-secret"})
    assert events.status_code == 200
    matching = [event for event in events.json()["data"] if event["request_id"] == "audit-auth"]
    assert matching
    assert matching[-1]["status_code"] == 401
    assert matching[-1]["authenticated"] is False

    raw = (tmp_path / ".orbit" / "audit.jsonl").read_text(encoding="utf-8")
    assert "super-secret" not in raw
