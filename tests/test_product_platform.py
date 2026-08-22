from __future__ import annotations
from fastapi.testclient import TestClient
from fastapi.responses import JSONResponse
from orbit.api.platform import router
from orbit.api.server import create_app
from orbit.core.app import OrbitApp
from orbit.core.config import OrbitConfig
from orbit.entrypoint import app as production_app

def _client(tmp_path):
    orbit=OrbitApp(OrbitConfig(data_dir=tmp_path/".orbit",api_key="secret"));api=create_app(orbit);api.include_router(router)
    @api.exception_handler(PermissionError)
    async def permission_error(request,exc):return JSONResponse(status_code=403,content={"detail":str(exc)})
    return TestClient(api)

def test_projects_conversations_knowledge_and_agent(tmp_path,monkeypatch):
    monkeypatch.setenv("ORBIT_ENABLE_DEMO_MODEL","true");client=_client(tmp_path);headers={"Authorization":"Bearer secret"}
    project=client.post("/v1/projects",headers=headers,json={"name":"Build","description":"ORBIT work"});assert project.status_code==200;pid=project.json()["id"]
    conversation=client.post(f"/v1/projects/{pid}/conversations",headers=headers,json={"title":"Main"});assert conversation.status_code==200;cid=conversation.json()["id"]
    message=client.post(f"/v1/conversations/{cid}/messages",headers=headers,json={"role":"user","content":"hello"});assert message.status_code==200
    fetched=client.get(f"/v1/conversations/{cid}",headers=headers);assert fetched.status_code==200 and fetched.json()["messages"][0]["content"]=="hello"
    renamed=client.patch(f"/v1/conversations/{cid}",headers=headers,json={"title":"Renamed"});assert renamed.status_code==200 and renamed.json()["title"]=="Renamed"
    listed=client.get("/v1/conversations",headers=headers,params={"project_id":pid});assert listed.status_code==200 and listed.json()["data"][0]["title"]=="Renamed"
    content="ORBIT local first retrieval system. "*100;doc=client.post(f"/v1/projects/{pid}/knowledge",headers=headers,json={"name":"notes","content":content});assert doc.status_code==200 and doc.json()["chunks"]>1
    hits=client.post(f"/v1/projects/{pid}/knowledge/search?q=local+ORBIT",headers=headers);assert hits.status_code==200 and hits.json()["data"] and "chunk_index" in hits.json()["data"][0]
    agent=client.post("/v1/agents",headers=headers,json={"name":"helper","model":"orbit-demo","capabilities":["inference"]});assert agent.status_code==200
    result=client.post(f"/v1/agents/{agent.json()['id']}/run",headers=headers,json={"role":"user","content":"agent smoke"});assert result.status_code==200 and "agent smoke" in result.json()["output"]

def test_conversation_delete(tmp_path):
    client=_client(tmp_path);headers={"Authorization":"Bearer secret"};p=client.post("/v1/projects",headers=headers,json={"name":"Delete me"}).json();c=client.post(f"/v1/projects/{p['id']}/conversations",headers=headers,json={}).json();assert client.delete(f"/v1/conversations/{c['id']}",headers=headers).status_code==200;assert client.get(f"/v1/conversations/{c['id']}",headers=headers).status_code==404

def test_tool_capability_gate_and_media(tmp_path,monkeypatch):
    monkeypatch.setenv("ORBIT_ENABLE_DEMO_MODEL","true");client=_client(tmp_path);headers={"Authorization":"Bearer secret"}
    assert client.post("/v1/tools",headers=headers,json={"name":"echo","description":"safe echo","capability":"tool:echo"}).status_code==200
    assert client.post("/v1/tools/echo/run",headers=headers,json={"arguments":{"text":"x"},"capabilities":[]}).status_code==403
    assert client.post("/v1/tools/echo/run",headers=headers,json={"arguments":{"text":"x"},"capabilities":["tool:echo"]}).status_code==200
    media=client.post("/v1/media",headers=headers,files={"file":("sample.txt",b"hello","text/plain")});assert media.status_code==200 and media.json()["sha256"]

def test_model_lifecycle_endpoints(tmp_path,monkeypatch):
    monkeypatch.setenv("ORBIT_ENABLE_DEMO_MODEL","true");client=_client(tmp_path);headers={"Authorization":"Bearer secret"};models=client.get("/v1/models",headers=headers);assert models.status_code==200;mid=models.json()["data"][0]["id"];assert client.post(f"/v1/models/{mid}/start",headers=headers).json()["state"]=="running";assert client.post(f"/v1/models/{mid}/stop",headers=headers).json()["state"]=="stopped"

def test_production_entrypoint_exposes_platform_contract():
    client=TestClient(production_app);response=client.get("/v1/platform");assert response.status_code in {200,401}
    if response.status_code==200:assert response.json()["modules"]["knowledge"] is True
    assert client.get("/control").status_code==200
