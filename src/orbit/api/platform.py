"""Persistent product-plane APIs: projects, knowledge, agents, tools and media."""
from __future__ import annotations
import hashlib, json, re, sqlite3, time
from pathlib import Path
from typing import Any
from fastapi import APIRouter, HTTPException, Request, UploadFile
from pydantic import BaseModel, Field
from orbit.api.runtime_control import RuntimeExecutor
from orbit.core.capabilities import CapabilitySet
from orbit.core.router import RouteRequest
from orbit.core.runtime import GenerationRequest
router = APIRouter(prefix="/v1", tags=["product"])
def _db(request: Request):
    context=request.app.state.orbit_context; path=Path(context.app.config.data_dir)/"platform.db"; path.parent.mkdir(parents=True,exist_ok=True)
    db=sqlite3.connect(path); db.row_factory=sqlite3.Row
    db.executescript("""CREATE TABLE IF NOT EXISTS projects(id TEXT PRIMARY KEY,name TEXT NOT NULL,description TEXT NOT NULL,created_at REAL NOT NULL);CREATE TABLE IF NOT EXISTS conversations(id TEXT PRIMARY KEY,project_id TEXT NOT NULL,title TEXT NOT NULL,created_at REAL NOT NULL,updated_at REAL NOT NULL);CREATE TABLE IF NOT EXISTS messages(id INTEGER PRIMARY KEY AUTOINCREMENT,conversation_id TEXT NOT NULL,role TEXT NOT NULL,content TEXT NOT NULL,created_at REAL NOT NULL);CREATE TABLE IF NOT EXISTS documents(id TEXT PRIMARY KEY,project_id TEXT NOT NULL,name TEXT NOT NULL,content TEXT NOT NULL,sha256 TEXT NOT NULL,created_at REAL NOT NULL);CREATE TABLE IF NOT EXISTS document_chunks(id TEXT PRIMARY KEY,document_id TEXT NOT NULL,project_id TEXT NOT NULL,chunk_index INTEGER NOT NULL,content TEXT NOT NULL,created_at REAL NOT NULL);CREATE INDEX IF NOT EXISTS idx_document_chunks_project ON document_chunks(project_id);CREATE TABLE IF NOT EXISTS tools(name TEXT PRIMARY KEY,description TEXT NOT NULL,capability TEXT NOT NULL,enabled INTEGER NOT NULL DEFAULT 1);CREATE TABLE IF NOT EXISTS agents(id TEXT PRIMARY KEY,name TEXT NOT NULL,model TEXT NOT NULL,capabilities TEXT NOT NULL,created_at REAL NOT NULL);CREATE TABLE IF NOT EXISTS media(id TEXT PRIMARY KEY,kind TEXT NOT NULL,name TEXT NOT NULL,mime_type TEXT NOT NULL,size_bytes INTEGER NOT NULL,sha256 TEXT NOT NULL,path TEXT NOT NULL,created_at REAL NOT NULL);""")
    return db
class ProjectIn(BaseModel): name:str=Field(min_length=1,max_length=120); description:str=Field(default="",max_length=1000)
class ConversationIn(BaseModel): title:str=Field(default="New conversation",min_length=1,max_length=160)
class ConversationPatch(BaseModel): title:str|None=Field(default=None,min_length=1,max_length=160)
class MessageIn(BaseModel): role:str=Field(min_length=1,max_length=32); content:str=Field(min_length=1,max_length=100000)
class KnowledgeIn(BaseModel): name:str=Field(min_length=1,max_length=240); content:str=Field(min_length=1,max_length=2_000_000)
class AgentIn(BaseModel): name:str=Field(min_length=1,max_length=120); model:str=Field(min_length=1,max_length=200); capabilities:list[str]=Field(default_factory=list)
class ToolIn(BaseModel): name:str=Field(min_length=1,max_length=80); description:str=Field(default="",max_length=500); capability:str=Field(default="tool:read",max_length=100)
class ToolRunIn(BaseModel): arguments:dict[str,Any]=Field(default_factory=dict); capabilities:list[str]=Field(default_factory=list)
def _row(row): return dict(row) if row else None
def _chunks(text,size=900,overlap=120):
    text="\n".join(x.rstrip() for x in text.replace("\r\n","\n").splitlines()).strip(); result=[]; start=0
    while text and start<len(text):
        end=min(len(text),start+size)
        if end<len(text):
            boundary=max(text.rfind("\n",start+size//2,end),text.rfind(" ",start+size//2,end))
            if boundary>start:end=boundary
        chunk=text[start:end].strip()
        if chunk:result.append(chunk)
        if end>=len(text):break
        start=max(start+1,end-overlap)
    return result
def _score(query,content):
    q=set(re.findall(r"[\w'-]+",query.lower())); c=re.findall(r"[\w'-]+",content.lower())
    if not q or not c:return 0.0
    overlap=len(q & set(c))/len(q); tf=sum(min(c.count(t),3) for t in q)/len(c)
    return overlap*0.9+min(tf*4,0.1)
@router.get("/platform")
async def platform(request):
    db=_db(request)
    try:return {"version":"0.5.0","modules":{"remote_runtime":True,"models":True,"projects":True,"knowledge":True,"agents":True,"tools":True,"mcp":True,"voice":True,"vision":True,"security":True,"packaging":True}}
    finally:db.close()
@router.get("/projects")
async def projects(request):
    db=_db(request)
    try:return {"object":"list","data":[dict(r) for r in db.execute("SELECT * FROM projects ORDER BY created_at DESC")],"count":db.execute("SELECT COUNT(*) FROM projects").fetchone()[0]}
    finally:db.close()
@router.post("/projects")
async def create_project(payload:ProjectIn,request):
    db=_db(request); pid=hashlib.sha256(f"{payload.name}:{time.time_ns()}".encode()).hexdigest()[:16]
    try:db.execute("INSERT INTO projects VALUES(?,?,?,?)",(pid,payload.name,payload.description,time.time()));db.commit();return {"id":pid,"name":payload.name,"description":payload.description}
    finally:db.close()
@router.get("/projects/{project_id}")
async def project(project_id,request):
    db=_db(request)
    try:
        row=_row(db.execute("SELECT * FROM projects WHERE id=?",(project_id,)).fetchone())
        if not row:raise HTTPException(404,"project not found")
        row["conversations"]=[dict(r) for r in db.execute("SELECT * FROM conversations WHERE project_id=? ORDER BY updated_at DESC",(project_id,))]
        row["documents"]=[dict(r) for r in db.execute("SELECT id,name,sha256,created_at,(SELECT COUNT(*) FROM document_chunks c WHERE c.document_id=documents.id) AS chunks FROM documents WHERE project_id=? ORDER BY created_at DESC",(project_id,))]
        return row
    finally:db.close()
@router.post("/projects/{project_id}/conversations")
async def create_conversation(project_id,payload:ConversationIn,request):
    db=_db(request)
    try:
        if not db.execute("SELECT 1 FROM projects WHERE id=?",(project_id,)).fetchone():raise HTTPException(404,"project not found")
        cid=hashlib.sha256(f"{project_id}:{time.time_ns()}".encode()).hexdigest()[:20];now=time.time();db.execute("INSERT INTO conversations VALUES(?,?,?,?,?)",(cid,project_id,payload.title,now,now));db.commit();return {"id":cid,"project_id":project_id,"title":payload.title,"created_at":now,"updated_at":now}
    finally:db.close()
@router.get("/conversations")
async def conversations(request,project_id:str|None=None):
    db=_db(request)
    try:
        rows=db.execute("SELECT * FROM conversations WHERE project_id=? ORDER BY updated_at DESC",(project_id,)) if project_id else db.execute("SELECT * FROM conversations ORDER BY updated_at DESC")
        return {"object":"list","data":[dict(r) for r in rows]}
    finally:db.close()
@router.get("/conversations/{conversation_id}")
async def conversation(conversation_id,request):
    db=_db(request)
    try:
        row=_row(db.execute("SELECT * FROM conversations WHERE id=?",(conversation_id,)).fetchone())
        if not row:raise HTTPException(404,"conversation not found")
        row["messages"]=[dict(r) for r in db.execute("SELECT id,role,content,created_at FROM messages WHERE conversation_id=? ORDER BY id",(conversation_id,))];return row
    finally:db.close()
@router.patch("/conversations/{conversation_id}")
async def rename_conversation(conversation_id,payload:ConversationPatch,request):
    if payload.title is None:raise HTTPException(422,"title is required")
    db=_db(request)
    try:
        if not db.execute("SELECT 1 FROM conversations WHERE id=?",(conversation_id,)).fetchone():raise HTTPException(404,"conversation not found")
        db.execute("UPDATE conversations SET title=?,updated_at=? WHERE id=?",(payload.title,time.time(),conversation_id));db.commit();return dict(db.execute("SELECT * FROM conversations WHERE id=?",(conversation_id,)).fetchone())
    finally:db.close()
@router.delete("/conversations/{conversation_id}")
async def delete_conversation(conversation_id,request):
    db=_db(request)
    try:
        if not db.execute("SELECT 1 FROM conversations WHERE id=?",(conversation_id,)).fetchone():raise HTTPException(404,"conversation not found")
        db.execute("DELETE FROM messages WHERE conversation_id=?",(conversation_id,));db.execute("DELETE FROM conversations WHERE id=?",(conversation_id,));db.commit();return {"deleted":True,"id":conversation_id}
    finally:db.close()
@router.post("/conversations/{conversation_id}/messages")
async def add_message(conversation_id,payload:MessageIn,request):
    db=_db(request)
    try:
        if not db.execute("SELECT 1 FROM conversations WHERE id=?",(conversation_id,)).fetchone():raise HTTPException(404,"conversation not found")
        now=time.time();cur=db.execute("INSERT INTO messages(conversation_id,role,content,created_at) VALUES(?,?,?,?)",(conversation_id,payload.role,payload.content,now));db.execute("UPDATE conversations SET updated_at=? WHERE id=?",(now,conversation_id));db.commit();return {"id":cur.lastrowid,"conversation_id":conversation_id,"role":payload.role,"content":payload.content,"created_at":now}
    finally:db.close()
@router.post("/projects/{project_id}/knowledge")
async def add_knowledge(project_id,payload:KnowledgeIn,request):
    db=_db(request)
    try:
        if not db.execute("SELECT 1 FROM projects WHERE id=?",(project_id,)).fetchone():raise HTTPException(404,"project not found")
        digest=hashlib.sha256(payload.content.encode()).hexdigest();did=hashlib.sha256(f"{project_id}:{digest}".encode()).hexdigest()[:20];chunks=_chunks(payload.content)
        db.execute("INSERT OR REPLACE INTO documents VALUES(?,?,?,?,?,?)",(did,project_id,payload.name,payload.content,digest,time.time()));db.execute("DELETE FROM document_chunks WHERE document_id=?",(did,))
        for i,chunk in enumerate(chunks):db.execute("INSERT INTO document_chunks VALUES(?,?,?,?,?,?)",(hashlib.sha256(f"{did}:{i}:{chunk}".encode()).hexdigest()[:24],did,project_id,i,chunk,time.time()))
        db.commit();return {"id":did,"name":payload.name,"sha256":digest,"indexed":True,"chunks":len(chunks)}
    finally:db.close()
@router.post("/projects/{project_id}/knowledge/search")
async def search_knowledge(project_id,request,q:str,limit:int=5):
    if not q.strip():raise HTTPException(422,"query must not be empty")
    db=_db(request)
    try:
        if not db.execute("SELECT 1 FROM projects WHERE id=?",(project_id,)).fetchone():raise HTTPException(404,"project not found")
        hits=[]
        for r in db.execute("SELECT c.id,c.document_id,c.chunk_index,c.content,d.name,d.sha256 FROM document_chunks c JOIN documents d ON d.id=c.document_id WHERE c.project_id=?",(project_id,)):
            score=_score(q,r["content"])
            if score>0:hits.append((score,dict(r)))
        hits.sort(key=lambda x:x[0],reverse=True);return {"query":q,"data":[{"id":x[1]["id"],"document_id":x[1]["document_id"],"name":x[1]["name"],"chunk_index":x[1]["chunk_index"],"score":round(x[0],6),"snippet":x[1]["content"][:1200],"sha256":x[1]["sha256"]} for x in hits[:max(1,min(limit,20))]]}
    finally:db.close()
@router.get("/tools")
async def tools(request):
    db=_db(request)
    try:return {"object":"list","data":[dict(r) for r in db.execute("SELECT name,description,capability,enabled FROM tools ORDER BY name")]}
    finally:db.close()
@router.post("/tools")
async def register_tool(payload:ToolIn,request):
    db=_db(request)
    try:db.execute("INSERT OR REPLACE INTO tools VALUES(?,?,?,1)",(payload.name,payload.description,payload.capability));db.commit();return {"name":payload.name,"description":payload.description,"capability":payload.capability,"enabled":True}
    finally:db.close()
@router.post("/tools/{name}/run")
async def run_tool(name,payload:ToolRunIn,request):
    db=_db(request)
    try:
        row=db.execute("SELECT * FROM tools WHERE name=? AND enabled=1",(name,)).fetchone()
        if not row:raise HTTPException(404,"tool not found or disabled")
        CapabilitySet(frozenset(payload.capabilities)).require(row["capability"]);args=payload.arguments
        if name=="echo":result=args.get("text","")
        elif name=="time":result=time.time()
        elif name=="health":result={"status":"ok"}
        else:raise HTTPException(422,"tool has no executable builtin adapter")
        return {"tool":name,"ok":True,"result":result}
    finally:db.close()
@router.post("/agents")
async def create_agent(payload:AgentIn,request):
    db=_db(request);aid=hashlib.sha256(f"{payload.name}:{time.time_ns()}".encode()).hexdigest()[:20]
    try:db.execute("INSERT INTO agents VALUES(?,?,?,?,?)",(aid,payload.name,payload.model,json.dumps(sorted(set(payload.capabilities))),time.time()));db.commit();return {"id":aid,"name":payload.name,"model":payload.model,"capabilities":sorted(set(payload.capabilities))}
    finally:db.close()
@router.get("/agents")
async def agents(request):
    db=_db(request)
    try:
        data=[]
        for r in db.execute("SELECT * FROM agents ORDER BY created_at DESC"):
            item=dict(r);item["capabilities"]=json.loads(item["capabilities"]);data.append(item)
        return {"object":"list","data":data}
    finally:db.close()
@router.post("/agents/{agent_id}/run")
async def run_agent(agent_id,payload:MessageIn,request):
    db=_db(request)
    try:
        row=db.execute("SELECT * FROM agents WHERE id=?",(agent_id,)).fetchone()
        if not row:raise HTTPException(404,"agent not found")
        model_id=row["model"]
    finally:db.close()
    app=request.app.state.orbit_context.app
    if app.router is None:raise HTTPException(503,"inference router unavailable")
    decision=await app.router.route(RouteRequest(model_id));result=await RuntimeExecutor(decision.plan.runtime).execute(GenerationRequest(prompt=payload.content,model=decision.model_id),request_id=getattr(request.state,"request_id",None))
    return {"agent_id":agent_id,"request_id":result.request_id,"model":decision.model_id,"runtime":decision.runtime_name,"output":result.text,"duration_ms":result.duration_ms}
@router.post("/mcp/tools/{name}")
async def mcp_tool(name,payload:ToolRunIn,request):return await run_tool(name,payload,request)
@router.post("/media")
async def upload_media(request:Request,file:UploadFile):
    context=request.app.state.orbit_context;root=Path(context.app.config.data_dir)/"media";root.mkdir(parents=True,exist_ok=True);data=await file.read();max_bytes=int(__import__('os').getenv("ORBIT_MAX_MEDIA_BYTES",str(25*1024*1024)))
    if len(data)>max_bytes:raise HTTPException(413,f"media exceeds configured limit of {max_bytes} bytes")
    digest=hashlib.sha256(data).hexdigest();mid=digest[:20];suffix=Path(file.filename or "upload.bin").suffix[:12];path=root/f"{mid}{suffix}";path.write_bytes(data);db=_db(request)
    try:
        kind="image" if (file.content_type or "").startswith("image/") else "audio" if (file.content_type or "").startswith("audio/") else "file";db.execute("INSERT OR REPLACE INTO media VALUES(?,?,?,?,?,?,?,?)",(mid,kind,file.filename or "upload.bin",file.content_type or "application/octet-stream",len(data),digest,str(path),time.time()));db.commit();return {"id":mid,"kind":kind,"name":file.filename,"mime_type":file.content_type,"size_bytes":len(data),"sha256":digest}
    finally:db.close()
@router.get("/media")
async def media(request):
    db=_db(request)
    try:return {"object":"list","data":[dict(r) for r in db.execute("SELECT id,kind,name,mime_type,size_bytes,sha256,created_at FROM media ORDER BY created_at DESC")]}
    finally:db.close()
