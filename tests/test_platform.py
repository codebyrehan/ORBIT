from fastapi.testclient import TestClient
from orbit.app import create_app

def test_platform_and_project_chat_route_exists(tmp_path, monkeypatch):
    monkeypatch.setenv("ORBIT_DATA_DIR", str(tmp_path))
    client=TestClient(create_app())
    platform=client.get("/v1/platform")
    assert platform.status_code==200
    assert platform.json()["modules"]["semantic_retrieval"] is True
    assert platform.json()["modules"]["rag_chat"] is True

def test_project_knowledge_semantic_search(tmp_path, monkeypatch):
    monkeypatch.setenv("ORBIT_DATA_DIR", str(tmp_path))
    client=TestClient(create_app())
    project=client.post("/v1/projects",json={"name":"RAG"}).json()
    pid=project["id"]
    added=client.post(f"/v1/projects/{pid}/knowledge",json={"name":"guide.md","content":"ORBIT uses project scoped semantic retrieval for knowledge."})
    assert added.status_code==200
    assert added.json()["indexed"] is True
    result=client.post(f"/v1/projects/{pid}/knowledge/search",params={"q":"semantic retrieval","limit":3})
    assert result.status_code==200
    assert result.json()["retrieval"]=="semantic"
    assert result.json()["data"]

def test_project_chat_requires_configured_model(tmp_path, monkeypatch):
    monkeypatch.setenv("ORBIT_DATA_DIR", str(tmp_path))
    monkeypatch.delenv("ORBIT_OPENAI_MODEL", raising=False)
    client=TestClient(create_app())
    pid=client.post("/v1/projects",json={"name":"Chat"}).json()["id"]
    response=client.post(f"/v1/projects/{pid}/chat",json={"content":"hello"})
    assert response.status_code in (503, 500)
