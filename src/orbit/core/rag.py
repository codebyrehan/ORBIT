"""Provider-neutral semantic retrieval helpers used by product APIs."""
from __future__ import annotations
import json
import sqlite3
from dataclasses import dataclass
from orbit.core.embeddings import cosine_similarity, embed

@dataclass(frozen=True, slots=True)
class RetrievalHit:
    chunk_id: str
    document_id: str
    document_name: str
    chunk_index: int
    content: str
    score: float
    sha256: str


def ensure_embedding_schema(db: sqlite3.Connection) -> None:
    db.execute("CREATE TABLE IF NOT EXISTS chunk_embeddings(chunk_id TEXT PRIMARY KEY, embedding TEXT NOT NULL, dimensions INTEGER NOT NULL, created_at REAL NOT NULL)")


def index_chunk(db: sqlite3.Connection, chunk_id: str, content: str, created_at: float) -> int:
    vector = embed(content)
    db.execute("INSERT OR REPLACE INTO chunk_embeddings(chunk_id,embedding,dimensions,created_at) VALUES(?,?,?,?)", (chunk_id, json.dumps(vector, separators=(",", ":")), len(vector), created_at))
    return len(vector)


def retrieve(db: sqlite3.Connection, project_id: str, query: str, limit: int = 5) -> list[RetrievalHit]:
    ensure_embedding_schema(db)
    qvec = embed(query)
    hits: list[RetrievalHit] = []
    rows = db.execute("""SELECT c.id,c.document_id,c.chunk_index,c.content,d.name,d.sha256,e.embedding
        FROM document_chunks c JOIN documents d ON d.id=c.document_id
        LEFT JOIN chunk_embeddings e ON e.chunk_id=c.id WHERE c.project_id=?""", (project_id,))
    for row in rows:
        vector = json.loads(row["embedding"]) if row["embedding"] else embed(row["content"])
        hits.append(RetrievalHit(row["id"], row["document_id"], row["name"], row["chunk_index"], row["content"], cosine_similarity(qvec, vector), row["sha256"]))
    hits.sort(key=lambda item: item.score, reverse=True)
    return hits[: max(1, min(limit, 20))]


def build_context(hits: list[RetrievalHit], max_chars: int = 6000) -> str:
    parts: list[str] = []
    used = 0
    for hit in hits:
        block = f"[Source: {hit.document_name}#{hit.chunk_index}]\n{hit.content.strip()}"
        if used + len(block) > max_chars:
            break
        parts.append(block)
        used += len(block)
    return "\n\n".join(parts)
