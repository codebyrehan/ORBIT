from __future__ import annotations

from fastapi.testclient import TestClient

from orbit.api.server import create_app
from orbit.core.app import OrbitApp
from orbit.core.config import OrbitConfig


def test_security_contract_with_configured_token(tmp_path) -> None:
    token = "orbit-test-token-0123456789abcdef0123456789abcdef"
    app = OrbitApp(OrbitConfig(data_dir=tmp_path, api_key=token, rate_limit_per_minute=120, rate_limit_burst=3))
    client = TestClient(create_app(app))

    assert client.get("/v1/metrics").status_code == 401
    assert client.get("/v1/metrics", headers={"Authorization": "Bearer invalid"}).status_code == 401

    response = client.get("/v1/metrics", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 200
    assert "requests_total" in response.json()


def test_security_contract_enforces_burst_limit(tmp_path) -> None:
    token = "orbit-test-token-0123456789abcdef0123456789abcdef"
    app = OrbitApp(OrbitConfig(data_dir=tmp_path, api_key=token, rate_limit_per_minute=120, rate_limit_burst=3))
    client = TestClient(create_app(app))
    headers = {"Authorization": f"Bearer {token}"}

    assert client.get("/v1/metrics", headers=headers).status_code == 200
    assert client.get("/v1/metrics", headers=headers).status_code == 200
    assert client.get("/v1/metrics", headers=headers).status_code == 200
    response = client.get("/v1/metrics", headers=headers)
    assert response.status_code == 429
    assert int(response.headers["Retry-After"]) >= 1
