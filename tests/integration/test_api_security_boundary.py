from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient

from orbit.api.server import create_app
from orbit.core.app import OrbitApp
from orbit.core.config import OrbitConfig


def test_protected_v1_endpoint_requires_bearer_token(tmp_path: Path) -> None:
    token = "t" * 32
    app = OrbitApp(OrbitConfig(data_dir=tmp_path / ".orbit", api_key=token))
    api = create_app(app)

    with TestClient(api) as client:
        unauthorized = client.get("/v1/system")
        authorized = client.get("/v1/system", headers={"Authorization": f"Bearer {token}"})

    assert unauthorized.status_code == 401
    assert unauthorized.headers["www-authenticate"] == "Bearer"
    assert authorized.status_code in {200, 503}


def test_invalid_bearer_token_is_rejected(tmp_path: Path) -> None:
    token = "t" * 32
    app = OrbitApp(OrbitConfig(data_dir=tmp_path / ".orbit", api_key=token))
    api = create_app(app)

    with TestClient(api) as client:
        response = client.get("/v1/system", headers={"Authorization": "Bearer " + "x" * 32})

    assert response.status_code == 401


def test_rate_limit_returns_retry_after(tmp_path: Path) -> None:
    token = "t" * 32
    app = OrbitApp(OrbitConfig(data_dir=tmp_path / ".orbit", api_key=token, rate_limit_per_minute=1, rate_limit_burst=1))
    api = create_app(app)

    headers = {"Authorization": f"Bearer {token}"}
    with TestClient(api) as client:
        first = client.get("/v1/system", headers=headers)
        second = client.get("/v1/system", headers=headers)

    assert first.status_code in {200, 503}
    assert second.status_code == 429
    assert "retry-after" in second.headers
