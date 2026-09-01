"""Object-store DDL and schema version.

A `STORE_SCHEMA_VERSION` mismatch is always a full rebuild, never a
migration: the store is disposable and rebuilds cheaply from the validated
export plus a per-file document scan, so there is nothing a migration path
would save that a rebuild does not already give for free.
"""

from __future__ import annotations

import sqlite3
from pathlib import Path

STORE_SCHEMA_VERSION = "hydra-framework.object-store.v1"

_DDL = (
    # Validated per file, on (mtime_ns, size) -- the freshness
    # contract for the tables scanning avoids re-reading.
    "CREATE TABLE documents ("
    "path TEXT PRIMARY KEY, mtime_ns INTEGER, size INTEGER, digest TEXT, "
    "handler TEXT, envelope_json TEXT, scanned_at TEXT)",
    "CREATE TABLE refs (src_path TEXT, dst_ref TEXT, line INTEGER)",
    "CREATE INDEX idx_refs_dst_ref ON refs(dst_ref)",
    # Rebuilt wholesale from the validated export, keyed to its content digest.
    "CREATE TABLE objects ("
    "hydra_id TEXT PRIMARY KEY, uid TEXT, path TEXT, digest TEXT, family TEXT, "
    "kind TEXT, status TEXT, tier TEXT, scope TEXT, schema_version INTEGER, "
    "title TEXT, envelope_path TEXT)",
    "CREATE INDEX idx_objects_uid ON objects(uid)",
    "CREATE INDEX idx_objects_path ON objects(path)",
    "CREATE INDEX idx_objects_digest ON objects(digest)",
    "CREATE TABLE aliases (alias TEXT PRIMARY KEY, hydra_id TEXT)",
    "CREATE TABLE relations (src_id TEXT, dst_id TEXT)",
    "CREATE INDEX idx_relations_dst_id ON relations(dst_id)",
    "CREATE TABLE provenance (hydra_id TEXT, source_path TEXT)",
    # Validated per file, same contract as `documents`.
    "CREATE TABLE tasks ("
    "path TEXT PRIMARY KEY, owner TEXT, name TEXT, status TEXT, updated TEXT, "
    "goal TEXT, blocked_on TEXT, mtime_ns INTEGER, size INTEGER)",
    "CREATE TABLE meta (key TEXT PRIMARY KEY, value TEXT)",
)


def default_store_path(local: Path) -> Path:
    return local / "index" / "object-store.db"


def create_schema(conn: sqlite3.Connection) -> None:
    for statement in _DDL:
        conn.execute(statement)
    conn.execute("INSERT INTO meta VALUES ('schema', ?)", (STORE_SCHEMA_VERSION,))


def store_meta(conn: sqlite3.Connection) -> dict[str, str]:
    try:
        return dict(conn.execute("SELECT key, value FROM meta").fetchall())
    except sqlite3.Error:
        return {}


def schema_matches(conn: sqlite3.Connection) -> bool:
    return store_meta(conn).get("schema") == STORE_SCHEMA_VERSION
