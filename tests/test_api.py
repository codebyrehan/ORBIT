from hashlib import sha256
from pathlib import Path

from fastapi.testclient import TestClient

from orbit.api.server import create_app
from orbit.core.app import OrbitApp
from orbit.core.config import OrbitConfig
from orbit.core.models import ModelSpec


def test_health_readiness_and_system_endpoints(tmp_path) -> None:
    app = OrbitApp(OrbitConfig(data_dir=tmp_path / ".orbit"))
    client = TestClient(create_app(app))

    health = client.get("/health")
    ready = client.get("/ready")
    system = client.get("/v1/system")

    assert health.status_code == 200
    assert health.json()["status"] == "ok"
    assert ready.status_code == 200
    assert ready.json() == {"ready": True}
    assert system.status_code == 200
    assert "architecture" in system.json()


def test_configured_api_key_protects_control_plane_but_not_health(tmp_path) -> None:
    app = OrbitApp(OrbitConfig(data_dir=tmp_path / ".orbit", api_key="secret-key"))
    client = TestClient(create_app(app))

    health = client.get("/health")
    missing = client.get("/v1/models")
    wrong = client.get("/v1/models", headers={"Authorization": "Bearer wrong"})
    valid = client.get("/v1/models", headers={"Authorization": "Bearer secret-key"})

    assert health.status_code == 200
    assert missing.status_code == 401
    assert wrong.status_code == 401
    assert missing.headers["www-authenticate"] == "Bearer"
    assert valid.status_code == 200


def test_models_endpoint_exposes_catalog(tmp_path) -> None:
    app = OrbitApp(OrbitConfig(data_dir=tmp_path / ".orbit"))
    app.start()
    app.models.register(ModelSpec("demo", "Demo", capabilities=frozenset({"chat"})))
    client = TestClient(create_app(app))

    response = client.get("/v1/models")

    assert response.status_code == 200
    assert response.json()["data"][0]["id"] == "demo"


def test_model_lifecycle_api_register_install_and_remove(tmp_path: Path) -> None:
    app = OrbitApp(OrbitConfig(data_dir=tmp_path / ".orbit"))
    app.start()
    client = TestClient(create_app(app))
    source = tmp_path / "demo.gguf"
    source.write_bytes(b"model-data")
    digest = sha256(source.read_bytes()).hexdigest()

    registered = client.post("/v1/models", json={"id": "demo", "display_name": "Demo", "size_bytes": source.stat().st_size, "capabilities": ["chat"]})
    assert registered.status_code == 200
    assert registered.json()["state"] == "registered"

    installed = client.post("/v1/models/demo/install", json={"source_path": str(source), "sha256": digest})
    assert installed.status_code == 200
    assert installed.json()["state"] == "ready"
    assert Path(installed.json()["path"]).exists()

    removed = client.delete("/v1/models/demo")
    assert removed.status_code == 200
    assert removed.json()["removed"] is True
    assert client.get("/v1/models/demo").status_code == 404


def test_model_install_rejects_bad_checksum(tmp_path: Path) -> None:
    app = OrbitApp(OrbitConfig(data_dir=tmp_path / ".orbit"))
    app.start()
    client = TestClient(create_app(app))
    source = tmp_path / "demo.gguf"
    source.write_bytes(b"model-data")

    assert client.post("/v1/models", json={"id": "demo", "display_name": "Demo"}).status_code == 200
    response = client.post("/v1/models/demo/install", json={"source_path": str(source), "sha256": "0" * 64})

    assert response.status_code == 422
    assert "checksum mismatch" in response.json()["detail"]


def test_chat_requires_runtime(tmp_path) -> None:
    app = OrbitApp(OrbitConfig(data_dir=tmp_path / ".orbit"))
    app.start()
    app.models.register(ModelSpec("demo", "Demo"))
    client = TestClient(create_app(app))

    response = client.post(
        "/v1/chat/completions",
        json={"model": "demo", "messages": [{"role": "user", "content": "hello"}]},
    )

    assert response.status_code == 503


def test_chat_rejects_unknown_model(tmp_path) -> None:
    app = OrbitApp(OrbitConfig(data_dir=tmp_path / ".orbit"))
    app.start()
    client = TestClient(create_app(app))

    response = client.post(
        "/v1/chat/completions",
        json={"model": "missing", "messages": [{"role": "user", "content": "hello"}]},
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "unknown model: missing"
