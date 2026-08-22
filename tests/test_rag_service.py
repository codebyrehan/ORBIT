import sqlite3

from orbit.core.rag import build_context, index_chunk, retrieve


def test_semantic_retrieval_is_project_scoped():
    db = sqlite3.connect(":memory:")
    db.row_factory = sqlite3.Row
    db.executescript("""
    CREATE TABLE documents(id TEXT PRIMARY KEY, project_id TEXT, name TEXT, content TEXT, sha256 TEXT);
    CREATE TABLE document_chunks(id TEXT PRIMARY KEY, document_id TEXT, project_id TEXT, chunk_index INTEGER, content TEXT);
    """)
    db.execute("INSERT INTO documents VALUES('d1','p1','python.md','python async runtime','x')")
    db.execute("INSERT INTO documents VALUES('d2','p2','python.md','python async runtime','y')")
    db.execute("INSERT INTO document_chunks VALUES('c1','d1','p1',0,'Python async runtime and await')")
    db.execute("INSERT INTO document_chunks VALUES('c2','d2','p2',0,'Python async runtime and await')")
    index_chunk(db, 'c1', 'Python async runtime and await', 1.0)
    index_chunk(db, 'c2', 'Python async runtime and await', 1.0)
    db.commit()
    hits = retrieve(db, 'p1', 'async runtime', 5)
    assert len(hits) == 1
    assert hits[0].chunk_id == 'c1'


def test_context_has_source_markers_and_respects_limit():
    db = sqlite3.connect(":memory:")
    db.row_factory = sqlite3.Row
    db.executescript("CREATE TABLE documents(id TEXT PRIMARY KEY, project_id TEXT, name TEXT, content TEXT, sha256 TEXT); CREATE TABLE document_chunks(id TEXT PRIMARY KEY, document_id TEXT, project_id TEXT, chunk_index INTEGER, content TEXT);")
    db.execute("INSERT INTO documents VALUES('d','p','guide.md','hello world','hash')")
    db.execute("INSERT INTO document_chunks VALUES('c','d','p',0,'hello world')")
    index_chunk(db, 'c', 'hello world', 1.0)
    db.commit()
    context = build_context(retrieve(db, 'p', 'hello', 1), max_chars=100)
    assert '[Source: guide.md#0]' in context
