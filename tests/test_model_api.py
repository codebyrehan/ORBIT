from pathlib import Path

from fastapi.testclient import TestClient

from orbit.api.server import create_app
from orbit.core.app import OrbitApp
from orbit.core.config import OrbitConfig
from orbit.core.models import ModelSpec


def test_model_detail_and_verification_endpoint(tmp_path: Path) -> None:
    app = OrbitApp(OrbitConfig.default(data_dir=tmp_path))
    client = TestClient(create_app(app))
    app.start()
    assert app.model_manager is not None
    app.model_manager.register(ModelSpec("demo", "Demo"))
    artifact = tmp_path / "demo.gguf"
    artifact.write_bytes(b"orbit-model")

    detail = client.get("/v1/models/demo")
    verify = client.post("/v1/models/demo/verify", json={"path": str(artifact)})

    assert detail.status_code == 200
    assert detail.json()["state"] == "registered"
    assert verify.status_code == 200
    assert verify.json()["verified"] is True


def test_model_verification_rejects_missing_artifact(tmp_path: Path) -> None:
    app = OrbitApp(OrbitConfig.default(data_dir=tmp_path))
    client = TestClient(create_app(app))
    app.start()
    assert app.model_manager is not None
    app.model_manager.register(ModelSpec("demo", "Demo"))

    response = client.post("/v1/models/demo/verify", json={"path": str(tmp_path / "missing.gguf")})

    assert response.status_code == 422
    assert "does not exist" in response.json()["detail"]
