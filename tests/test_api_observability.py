from fastapi.testclient import TestClient

from orbit.api.server import create_app
from orbit.core.app import OrbitApp
from orbit.core.config import OrbitConfig


def test_request_id_is_propagated_and_metrics_are_exposed(tmp_path) -> None:
    app = OrbitApp(OrbitConfig.default(data_dir=tmp_path))
    client = TestClient(create_app(app))

    response = client.get("/health", headers={"x-request-id": "test-request-1"})
    metrics = client.get("/v1/metrics")

    assert response.status_code == 200
    assert response.headers["x-request-id"] == "test-request-1"
    assert metrics.status_code == 200
    assert metrics.json()["requests_total"] == 0


def test_metrics_start_empty(tmp_path) -> None:
    app = OrbitApp(OrbitConfig.default(data_dir=tmp_path))
    client = TestClient(create_app(app))
    payload = client.get("/v1/metrics").json()
    assert payload == {
        "requests_total": 0,
        "requests_failed": 0,
        "tokens_total": 0,
        "latency_ms_total": 0.0,
        "latency_ms_avg": 0.0,
        "error_rate": 0.0,
    }
