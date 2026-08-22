"""Small, idempotent SQLite migration runner for ORBIT product data."""
from __future__ import annotations
import sqlite3
from collections.abc import Callable

Migration = tuple[int, str, Callable[[sqlite3.Connection], None]]


def _m1(db: sqlite3.Connection) -> None:
    db.execute("CREATE TABLE IF NOT EXISTS schema_migrations(version INTEGER PRIMARY KEY, name TEXT NOT NULL, applied_at REAL NOT NULL)")


def _m2(db: sqlite3.Connection) -> None:
    db.execute("CREATE TABLE IF NOT EXISTS chunk_embeddings(chunk_id TEXT PRIMARY KEY, embedding TEXT NOT NULL, dimensions INTEGER NOT NULL, created_at REAL NOT NULL)")
    db.execute("CREATE INDEX IF NOT EXISTS idx_chunk_embeddings_dimensions ON chunk_embeddings(dimensions)")


MIGRATIONS: tuple[Migration, ...] = ((1, "schema_migrations", _m1), (2, "chunk_embeddings", _m2))


def migrate(db: sqlite3.Connection, now: float) -> int:
    db.execute("CREATE TABLE IF NOT EXISTS schema_migrations(version INTEGER PRIMARY KEY, name TEXT NOT NULL, applied_at REAL NOT NULL)")
    applied = {row[0] for row in db.execute("SELECT version FROM schema_migrations")}
    latest = max(applied, default=0)
    for version, name, fn in MIGRATIONS:
        if version in applied:
            continue
        fn(db)
        db.execute("INSERT INTO schema_migrations(version,name,applied_at) VALUES(?,?,?)", (version, name, now))
        latest = version
    db.commit()
    return latest
