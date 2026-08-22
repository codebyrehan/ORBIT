from __future__ import annotations

from fastapi.testclient import TestClient

from orbit.api.server import create_app
from orbit.core.app import OrbitApp
from orbit.core.config import OrbitConfig


def test_dashboard_and_authenticated_session(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("ORBIT_ENABLE_DEMO_MODEL", "true")
    app = OrbitApp(OrbitConfig(data_dir=tmp_path / ".orbit", api_key="secret"))
    client = TestClient(create_app(app))

    root = client.get("/", headers={"Accept": "text/html"})
    assert root.status_code == 200
    assert "ORBIT" in root.text
    assert "Inference" in root.text

    assert client.get("/v1/session").status_code == 401
    session = client.get("/v1/session", headers={"Authorization": "Bearer secret"})
    assert session.status_code == 200
    assert session.json()["authenticated"] is True


def test_demo_model_end_to_end_inference(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("ORBIT_ENABLE_DEMO_MODEL", "true")
    app = OrbitApp(OrbitConfig(data_dir=tmp_path / ".orbit", api_key="secret"))
    client = TestClient(create_app(app))
    headers = {"Authorization": "Bearer secret"}

    models = client.get("/v1/models", headers=headers)
    assert models.status_code == 200
    assert any(item["id"] == "orbit-demo" for item in models.json()["data"])

    response = client.post("/v1/chat/completions", headers=headers, json={"model": "orbit-demo", "messages": [{"role": "user", "content": "hello ORBIT"}]})
    assert response.status_code == 200
    body = response.json()
    assert body["object"] == "chat.completion"
    assert body["runtime"] == "orbit-demo"
    assert "hello ORBIT" in body["choices"][0]["message"]["content"]

    requests = client.get("/v1/requests", headers=headers)
    assert requests.status_code == 200
    assert requests.json()["data"]
    assert requests.json()["data"][0]["state"] == "completed"
