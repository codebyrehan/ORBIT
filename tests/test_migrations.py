import sqlite3

from orbit.core.migrations import migrate


def test_migrations_are_idempotent():
    db = sqlite3.connect(":memory:")
    assert migrate(db, 1.0) == 2
    assert migrate(db, 2.0) == 2
    rows = db.execute("SELECT version,name FROM schema_migrations ORDER BY version").fetchall()
    assert rows == [(1, "schema_migrations"), (2, "chunk_embeddings")]
