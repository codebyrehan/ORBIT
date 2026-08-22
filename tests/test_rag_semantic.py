from __future__ import annotations
import sqlite3
from orbit.core.rag import build_context, index_chunk, retrieve


def test_semantic_retrieval_and_context():
    db = sqlite3.connect(":memory:")
    db.row_factory = sqlite3.Row
    db.executescript("""
    CREATE TABLE documents(id TEXT PRIMARY KEY, project_id TEXT, name TEXT, content TEXT, sha256 TEXT, created_at REAL);
    CREATE TABLE document_chunks(id TEXT PRIMARY KEY, document_id TEXT, project_id TEXT, chunk_index INTEGER, content TEXT, created_at REAL);
    INSERT INTO documents VALUES ('d1','p1','notes.md','local inference notes','abc',1);
    INSERT INTO documents VALUES ('d2','p1','other.md','unrelated gardening notes','def',1);
    INSERT INTO document_chunks VALUES ('c1','d1','p1',0,'ORBIT local inference runtime and model routing',1);
    INSERT INTO document_chunks VALUES ('c2','d2','p1',0,'tomato soil watering schedule',1);
    """)
    index_chunk(db, 'c1', 'ORBIT local inference runtime and model routing', 1)
    index_chunk(db, 'c2', 'tomato soil watering schedule', 1)
    db.commit()
    hits = retrieve(db, 'p1', 'local model inference', 2)
    assert hits and hits[0].chunk_id == 'c1'
    context = build_context(hits)
    assert '[Source: notes.md#0]' in context
    assert 'local inference' in context
