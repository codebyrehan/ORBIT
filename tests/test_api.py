from fastapi.testclient import TestClient

from orbit.api.server import create_app
from orbit.core.app import OrbitApp
from orbit.core.config import OrbitConfig
from orbit.core.models import ModelSpec


def test_health_and_system_endpoints(tmp_path):
    app = OrbitApp(OrbitConfig(data_dir=tmp_path / ".orbit"))
    client = TestClient(create_app(app))

    health = client.get("/health")
    system = client.get("/v1/system")

    assert health.status_code == 200
    assert health.json()["status"] == "ok"
    assert system.status_code == 200
    assert "architecture" in system.json()


def test_models_endpoint_exposes_catalog(tmp_path):
    app = OrbitApp(OrbitConfig(data_dir=tmp_path / ".orbit"))
    app.start()
    app.models.register(ModelSpec("demo", "Demo", capabilities=frozenset({"chat"})))
    client = TestClient(create_app(app))

    response = client.get("/v1/models")

    assert response.status_code == 200
    assert response.json()["data"][0]["id"] == "demo"


def test_chat_requires_runtime(tmp_path):
    app = OrbitApp(OrbitConfig(data_dir=tmp_path / ".orbit"))
    app.start()
    app.models.register(ModelSpec("demo", "Demo"))
    client = TestClient(create_app(app))

    response = client.post(
        "/v1/chat/completions",
        json={"model": "demo", "messages": [{"role": "user", "content": "hello"}]},
    )

    assert response.status_code == 503
