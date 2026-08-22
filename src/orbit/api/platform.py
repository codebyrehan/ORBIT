"""Persistent product-plane APIs: projects, knowledge, agents, tools and media."""
from __future__ import annotations

import hashlib
import json
import sqlite3
import time
from pathlib import Path
from typing import Any

from fastapi import APIRouter, HTTPException, Request, UploadFile
from pydantic import BaseModel, Field

from orbit.core.capabilities import CapabilitySet
from orbit.core.model_manager import ModelState
from orbit.core.router import RouteRequest
from orbit.core.runtime import GenerationRequest
from orbit.api.runtime_control import RuntimeExecutor

router = APIRouter(prefix="/v1", tags=["product"])


def _db(request: Request) -> sqlite3.Connection:
    context = request.app.state.orbit_context
    path = Path(context.app.config.data_dir) / "platform.db"
    path.parent.mkdir(parents=True, exist_ok=True)
    db = sqlite3.connect(path)
    db.row_factory = sqlite3.Row
    db.executescript("""
    CREATE TABLE IF NOT EXISTS projects(id TEXT PRIMARY KEY,name TEXT NOT NULL,description TEXT NOT NULL,created_at REAL NOT NULL);
    CREATE TABLE IF NOT EXISTS conversations(id TEXT PRIMARY KEY,project_id TEXT NOT NULL,title TEXT NOT NULL,created_at REAL NOT NULL,updated_at REAL NOT NULL);
    CREATE TABLE IF NOT EXISTS messages(id INTEGER PRIMARY KEY AUTOINCREMENT,conversation_id TEXT NOT NULL,role TEXT NOT NULL,content TEXT NOT NULL,created_at REAL NOT NULL);
    CREATE TABLE IF NOT EXISTS documents(id TEXT PRIMARY KEY,project_id TEXT NOT NULL,name TEXT NOT NULL,content TEXT NOT NULL,sha256 TEXT NOT NULL,created_at REAL NOT NULL);
    CREATE TABLE IF NOT EXISTS document_chunks(id TEXT PRIMARY KEY,document_id TEXT NOT NULL,project_id TEXT NOT NULL,chunk_index INTEGER NOT NULL,content TEXT NOT NULL,created_at REAL NOT NULL);
    CREATE INDEX IF NOT EXISTS idx_document_chunks_project ON document_chunks(project_id);
    CREATE TABLE IF NOT EXISTS tools(name TEXT PRIMARY KEY,description TEXT NOT NULL,capability TEXT NOT NULL,enabled INTEGER NOT NULL DEFAULT 1);
    CREATE TABLE IF NOT EXISTS agents(id TEXT PRIMARY KEY,name TEXT NOT NULL,model TEXT NOT NULL,capabilities TEXT NOT NULL,created_at REAL NOT NULL);
    CREATE TABLE IF NOT EXISTS media(id TEXT PRIMARY KEY,kind TEXT NOT NULL,name TEXT NOT NULL,mime_type TEXT NOT NULL,size_bytes INTEGER NOT NULL,sha256 TEXT NOT NULL,path TEXT NOT NULL,created_at REAL NOT NULL);
    """)
    return db


class ProjectIn(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    description: str = Field(default="", max_length=1000)

class ConversationIn(BaseModel):
    title: str = Field(default="New conversation", min_length=1, max_length=160)

class MessageIn(BaseModel):
    role: str = Field(min_length=1, max_length=32)
    content: str = Field(min_length=1, max_length=100000)

class KnowledgeIn(BaseModel):
    name: str = Field(min_length=1, max_length=240)
    content: str = Field(min_length=1, max_length=2_000_000)

class AgentIn(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    model: str = Field(min_length=1, max_length=200)
    capabilities: list[str] = Field(default_factory=list)

class ToolIn(BaseModel):
    name: str = Field(min_length=1, max_length=80)
    description: str = Field(default="", max_length=500)
    capability: str = Field(default="tool:read", max_length=100)

class ToolRunIn(BaseModel):
    arguments: dict[str, Any] = Field(default_factory=dict)
    capabilities: list[str] = Field(default_factory=list)


def _row(row: sqlite3.Row | None) -> dict[str, Any] | None:
    return dict(row) if row else None


def _chunks(text: str, size: int = 900, overlap: int = 120) -> list[str]:
    normalized = "\n".join(line.rstrip() for line in text.replace("\r\n", "\n").splitlines()).strip()
    if not normalized:
        return []
    result: list[str] = []
    start = 0
    while start < len(normalized):
        end = min(len(normalized), start + size)
        if end < len(normalized):
            boundary = max(normalized.rfind("\n", start + size // 2, end), normalized.rfind(" ", start + size // 2, end))
            if boundary > start:
                end = boundary
        chunk = normalized[start:end].strip()
        if chunk:
            result.append(chunk)
        if end >= len(normalized):
            break
        start = max(start + 1, end - overlap)
    return result


@router.get("/platform")
async def platform(request: Request) -> dict[str, Any]:
    db = _db(request)
    try:
        return {"version": "0.4.0", "modules": {"remote_runtime": True, "models": True, "projects": True, "knowledge": True, "agents": True, "tools": True, "mcp": True, "voice": True, "vision": True, "security": True, "packaging": True}}
    finally:
        db.close()


@router.get("/projects")
async def projects(request: Request) -> dict[str, Any]:
    db = _db(request)
    try:
        return {"object": "list", "data": [dict(r) for r in db.execute("SELECT * FROM projects ORDER BY created_at DESC")], "count": db.execute("SELECT COUNT(*) FROM projects").fetchone()[0]}
    finally: db.close()


@router.post("/projects")
async def create_project(payload: ProjectIn, request: Request) -> dict[str, Any]:
    db = _db(request); project_id = hashlib.sha256(f"{payload.name}:{time.time_ns()}".encode()).hexdigest()[:16]
    try:
        db.execute("INSERT INTO projects VALUES(?,?,?,?)", (project_id, payload.name, payload.description, time.time())); db.commit()
        return {"id": project_id, "name": payload.name, "description": payload.description}
    finally: db.close()


@router.get("/projects/{project_id}")
async def project(project_id: str, request: Request) -> dict[str, Any]:
    db = _db(request)
    try:
        row = _row(db.execute("SELECT * FROM projects WHERE id=?", (project_id,)).fetchone())
        if not row: raise HTTPException(404, "project not found")
        row["conversations"] = [dict(r) for r in db.execute("SELECT * FROM conversations WHERE project_id=? ORDER BY updated_at DESC", (project_id,))]
        row["documents"] = [dict(r) for r in db.execute("SELECT id,name,sha256,created_at,(SELECT COUNT(*) FROM document_chunks c WHERE c.document_id=documents.id) AS chunks FROM documents WHERE project_id=? ORDER BY created_at DESC", (project_id,))]
        return row
    finally: db.close()


@router.post("/projects/{project_id}/conversations")
async def create_conversation(project_id: str, payload: ConversationIn, request: Request) -> dict[str, Any]:
    db = _db(request)
    try:
        if not db.execute("SELECT 1 FROM projects WHERE id=?", (project_id,)).fetchone(): raise HTTPException(404, "project not found")
        cid = hashlib.sha256(f"{project_id}:{time.time_ns()}".encode()).hexdigest()[:20]; now=time.time()
        db.execute("INSERT INTO conversations VALUES(?,?,?,?,?)", (cid,project_id,payload.title,now,now)); db.commit(); return {"id":cid,"project_id":project_id,"title":payload.title,"created_at":now,"updated_at":now}
    finally: db.close()


@router.get("/conversations/{conversation_id}")
async def conversation(conversation_id: str, request: Request) -> dict[str, Any]:
    db=_db(request)
    try:
        row=_row(db.execute("SELECT * FROM conversations WHERE id=?",(conversation_id,)).fetchone())
        if not row: raise HTTPException(404,"conversation not found")
        row["messages"]=[dict(r) for r in db.execute("SELECT id,role,content,created_at FROM messages WHERE conversation_id=? ORDER BY id",(conversation_id,))]
        return row
    finally: db.close()


@router.post("/conversations/{conversation_id}/messages")
async def add_message(conversation_id: str, payload: MessageIn, request: Request) -> dict[str, Any]:
    db=_db(request)
    try:
        if not db.execute("SELECT 1 FROM conversations WHERE id=?",(conversation_id,)).fetchone(): raise HTTPException(404,"conversation not found")
        now=time.time(); cur=db.execute("INSERT INTO messages(conversation_id,role,content,created_at) VALUES(?,?,?,?)",(conversation_id,payload.role,payload.content,now)); db.execute("UPDATE conversations SET updated_at=? WHERE id=?",(now,conversation_id)); db.commit(); return {"id":cur.lastrowid,"conversation_id":conversation_id,"role":payload.role,"content":payload.content,"created_at":now}
    finally: db.close()


@router.post("/projects/{project_id}/knowledge")
async def add_knowledge(project_id: str, payload: KnowledgeIn, request: Request) -> dict[str, Any]:
    db=_db(request)
    try:
        if not db.execute("SELECT 1 FROM projects WHERE id=?",(project_id,)).fetchone(): raise HTTPException(404,"project not found")
        digest=hashlib.sha256(payload.content.encode()).hexdigest(); did=hashlib.sha256(f"{project_id}:{digest}".encode()).hexdigest()[:20]
        chunks = _chunks(payload.content)
        db.execute("INSERT OR REPLACE INTO documents VALUES(?,?,?,?,?,?)",(did,project_id,payload.name,payload.content,digest,time.time()))
        db.execute("DELETE FROM document_chunks WHERE document_id=?", (did,))
        for index, chunk in enumerate(chunks):
            chunk_id = hashlib.sha256(f"{did}:{index}:{chunk}".encode()).hexdigest()[:24]
            db.execute("INSERT INTO document_chunks VALUES(?,?,?,?,?,?)", (chunk_id,did,project_id,index,chunk,time.time()))
        db.commit(); return {"id":did,"name":payload.name,"sha256":digest,"indexed":True,"chunks":len(chunks)}
    finally: db.close()


@router.post("/projects/{project_id}/knowledge/search")
async def search_knowledge(project_id: str, request: Request, q: str, limit: int = 5) -> dict[str, Any]:
    if not q.strip(): raise HTTPException(422, "query must not be empty")
    db=_db(request)
    try:
        if not db.execute("SELECT 1 FROM projects WHERE id=?",(project_id,)).fetchone(): raise HTTPException(404,"project not found")
        terms={x.lower() for x in q.split() if x.strip()}
        hits=[]
        for r in db.execute("SELECT c.id,c.document_id,c.chunk_index,c.content,d.name,d.sha256 FROM document_chunks c JOIN documents d ON d.id=c.document_id WHERE c.project_id=?",(project_id,)):
            text=r["content"].lower()
            term_scores={t:text.count(t) for t in terms}
            matched=sum(term_scores.values())
            if matched:
                density=matched / max(1, len(text.split()))
                score=matched + density * 10
                hits.append((score,dict(r)))
        hits.sort(key=lambda x:x[0],reverse=True)
        return {"query":q,"data":[{"id":x[1]["id"],"document_id":x[1]["document_id"],"name":x[1]["name"],"chunk_index":x[1]["chunk_index"],"score":round(x[0],6),"snippet":x[1]["content"][:1200],"sha256":x[1]["sha256"]} for x in hits[:max(1,min(limit,20))]]}
    finally: db.close()


@router.get("/tools")
async def tools(request: Request) -> dict[str, Any]:
    db=_db(request)
    try: return {"object":"list","data":[dict(r) for r in db.execute("SELECT name,description,capability,enabled FROM tools ORDER BY name")]}
    finally: db.close()


@router.post("/tools")
async def register_tool(payload: ToolIn, request: Request) -> dict[str, Any]:
    db=_db(request)
    try:
        db.execute("INSERT OR REPLACE INTO tools VALUES(?,?,?,1)",(payload.name,payload.description,payload.capability)); db.commit(); return {"name":payload.name,"description":payload.description,"capability":payload.capability,"enabled":True}
    finally: db.close()


@router.post("/tools/{name}/run")
async def run_tool(name: str, payload: ToolRunIn, request: Request) -> dict[str, Any]:
    db=_db(request)
    try:
        row=db.execute("SELECT * FROM tools WHERE name=? AND enabled=1",(name,)).fetchone()
        if not row: raise HTTPException(404,"tool not found or disabled")
        CapabilitySet(frozenset(payload.capabilities)).require(row["capability"])
        args=payload.arguments
        if name == "echo": result=args.get("text","")
        elif name == "time": result=time.time()
        elif name == "health": result={"status":"ok"}
        else: raise HTTPException(422,"tool has no executable builtin adapter")
        return {"tool":name,"ok":True,"result":result}
    finally: db.close()


@router.post("/agents")
async def create_agent(payload: AgentIn, request: Request) -> dict[str, Any]:
    db=_db(request); aid=hashlib.sha256(f"{payload.name}:{time.time_ns()}".encode()).hexdigest()[:20]
    try:
        db.execute("INSERT INTO agents VALUES(?,?,?,?,?)",(aid,payload.name,payload.model,json.dumps(sorted(set(payload.capabilities))),time.time())); db.commit(); return {"id":aid,"name":payload.name,"model":payload.model,"capabilities":sorted(set(payload.capabilities))}
    finally: db.close()


@router.get("/agents")
async def agents(request: Request) -> dict[str, Any]:
    db=_db(request)
    try:
        data=[]
        for r in db.execute("SELECT * FROM agents ORDER BY created_at DESC"):
            item=dict(r); item["capabilities"]=json.loads(item["capabilities"]); data.append(item)
        return {"object":"list","data":data}
    finally: db.close()


@router.post("/agents/{agent_id}/run")
async def run_agent(agent_id: str, payload: MessageIn, request: Request) -> dict[str, Any]:
    db=_db(request)
    try:
        row=db.execute("SELECT * FROM agents WHERE id=?",(agent_id,)).fetchone()
        if not row: raise HTTPException(404,"agent not found")
        model_id=row["model"]
    finally: db.close()
    context=request.app.state.orbit_context; app=context.app
    if app.router is None: raise HTTPException(503,"inference router unavailable")
    decision=await app.router.route(RouteRequest(model_id))
    result=await RuntimeExecutor(decision.plan.runtime).execute(GenerationRequest(prompt=payload.content,model=decision.model_id),request_id=getattr(request.state,"request_id",None))
    return {"agent_id":agent_id,"request_id":result.request_id,"model":decision.model_id,"runtime":decision.runtime_name,"output":result.text,"duration_ms":result.duration_ms}


@router.post("/mcp/tools/{name}")
async def mcp_tool(name: str, payload: ToolRunIn, request: Request) -> dict[str, Any]:
    """MCP-compatible HTTP shim using the same capability gate as native tools."""
    return await run_tool(name,payload,request)


@router.post("/media")
async def upload_media(request: Request, file: UploadFile) -> dict[str, Any]:
    context=request.app.state.orbit_context; root=Path(context.app.config.data_dir)/"media"; root.mkdir(parents=True,exist_ok=True)
    data=await file.read(); max_bytes=int(__import__('os').getenv("ORBIT_MAX_MEDIA_BYTES", str(25*1024*1024)))
    if len(data) > max_bytes: raise HTTPException(413, f"media exceeds configured limit of {max_bytes} bytes")
    digest=hashlib.sha256(data).hexdigest(); media_id=digest[:20]; suffix=Path(file.filename or "upload.bin").suffix[:12]; path=root/f"{media_id}{suffix}"; path.write_bytes(data)
    kind="image" if (file.content_type or "").startswith("image/") else "audio" if (file.content_type or "").startswith("audio/") else "file"
    db=_db(request)
    try:
        db.execute("INSERT OR REPLACE INTO media VALUES(?,?,?,?,?,?,?,?)",(media_id,kind,file.filename or path.name,file.content_type or "application/octet-stream",len(data),digest,str(path),time.time())); db.commit()
    finally: db.close()
    return {"id":media_id,"kind":kind,"name":file.filename or path.name,"mime_type":file.content_type,"size_bytes":len(data),"sha256":digest,"stored":True,"inference_ready":kind in {"image","audio"}}


@router.get("/media")
async def media(request: Request) -> dict[str, Any]:
    db=_db(request)
    try: return {"object":"list","data":[dict(r) for r in db.execute("SELECT id,kind,name,mime_type,size_bytes,sha256,created_at FROM media ORDER BY created_at DESC")]}
    finally: db.close()


@router.post("/models/{model_id}/start")
async def start_model(model_id: str, request: Request) -> dict[str, Any]:
    context=request.app.state.orbit_context; manager=context.app.model_manager
    if manager is None: raise HTTPException(503,"model manager unavailable")
    current=manager.get(model_id)
    if current is None: raise HTTPException(404,f"unknown model: {model_id}")
    try:
        managed=manager.mark_running(model_id)
    except ValueError as exc: raise HTTPException(422,str(exc)) from exc
    return {"id":model_id,"state":managed.state.value,"runtime":sorted(managed.spec.runtimes)}


@router.post("/models/{model_id}/stop")
async def stop_model(model_id: str, request: Request) -> dict[str, Any]:
    context=request.app.state.orbit_context; manager=context.app.model_manager
    if manager is None: raise HTTPException(503,"model manager unavailable")
    current=manager.get(model_id)
    if current is None: raise HTTPException(404,f"unknown model: {model_id}")
    managed=manager.mark_stopped(model_id)
    return {"id":model_id,"state":managed.state.value}


@router.get("/packaging")
async def packaging(request: Request) -> dict[str, Any]:
    return {"product":"orbit-ai","install":"pip install orbit-ai","container":"docker build -t orbit-ai .","entrypoint":"uvicorn orbit.entrypoint:app --host 0.0.0.0 --port 8787","platforms":["linux","windows","macos"],"local_first":True,"state_dir":str(Path(request.app.state.orbit_context.app.config.data_dir))}