from __future__ import annotations

from fastapi.testclient import TestClient

from orbit.api.server import create_app
from orbit.core.app import OrbitApp
from orbit.core.config import OrbitConfig


def test_root_is_a_public_production_landing_endpoint(tmp_path) -> None:
    app = OrbitApp(OrbitConfig(data_dir=tmp_path))
    client = TestClient(create_app(app))

    response = client.get("/")

    assert response.status_code == 200
    assert response.json() == {
        "service": "ORBIT API",
        "status": "ok",
        "docs": "/docs",
        "health": "/health",
        "ready": "/ready",
    }
