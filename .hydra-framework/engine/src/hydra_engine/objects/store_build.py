"""Populate the operational object store from validated canonical state.

Two independent freshness models, matched to what each table derives from:

- `objects`/`aliases`/`relations`/`provenance` rebuild wholesale from the
  validated export (`objects/registry.py`'s `registry_object_entries`) --
  never from canonical metadata directly, and never the reverse. A stale
  export is already an error
  (`ref check`/`validate`), so the export is trustworthy input that costs
  0.004s to parse instead of a full tree scan.
- `documents`/`refs` are validated per file, on `(mtime_ns, size)`.
  `rebuild_documents_and_refs` does the one full scan a first build cannot
  avoid; `repair_stale_documents` re-reads only what changed since, which is
  the whole reason these two tables exist.

Both tables are populated inside `ports.sqlite_db.rebuild_atomically`'s
temp-then-swap by `rebuild_store`, so a reader never observes a half-built
store; `repair_stale_documents` writes directly to an already-built store,
since it only ever adds or replaces individual rows, never leaves the schema
itself incomplete.
"""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path

from hydra_engine.documents.digests import normalized_digest
from hydra_engine.documents.tokens import display_path, read_text
from hydra_engine.identity.hydra_ids import hydra_refs_by_line
from hydra_engine.objects.discovery import extract_hydra_object, extract_sidecar_objects, object_metadata_paths
from hydra_engine.objects.registry import registry_object_entries
from hydra_engine.objects.store_schema import create_schema, default_store_path, schema_matches, store_meta
from hydra_engine.ports import clock
from hydra_engine.ports.sqlite_db import connect_existing
from hydra_engine.ports.sqlite_db import rebuild_atomically


def export_digest(paths: ObjectLocations) -> str | None:
    """Content digest of the export the `objects`/`aliases`/`relations`/
    `provenance` tables are keyed to, or `None` if there is no export yet
    (a store cannot be built ahead of `ref index`)."""
    if not paths.object_registry.exists():
        return None
    return normalized_digest(paths.object_registry)


def _populate_object_tables(conn: sqlite3.Connection, paths: ObjectLocations, digest: str) -> int:
    entries, errors = registry_object_entries(paths.object_registry, paths.root)
    if errors:
        return 0
    for hydra_id, entry in entries.items():
        conn.execute(
            "INSERT INTO objects VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                hydra_id, entry.get("uid", ""), entry.get("path", ""), entry.get("digest", ""),
                entry.get("family", ""), entry.get("kind", ""), entry.get("status", ""),
                entry.get("tier", ""), entry.get("scope", ""), entry.get("schema_version", ""),
                entry.get("title", ""), entry.get("envelope_path") or entry.get("path", ""),
            ),
        )
        for alias in entry.get("aliases") or []:
            conn.execute("INSERT OR REPLACE INTO aliases VALUES (?, ?)", (alias, hydra_id))
        for relation in entry.get("relations") or []:
            conn.execute("INSERT INTO relations VALUES (?, ?)", (hydra_id, relation))
        for source in entry.get("provenance_sources") or []:
            conn.execute("INSERT INTO provenance VALUES (?, ?)", (hydra_id, source))
    conn.execute("INSERT OR REPLACE INTO meta VALUES ('export_digest', ?)", (digest,))
    return len(entries)


def _document_row(path: Path, paths: ObjectLocations) -> tuple:
    stat = path.stat()
    envelope, discovery_error = extract_hydra_object(path, paths)
    objects_here = [] if discovery_error else ([envelope] if envelope else [])
    if not discovery_error:
        sidecar_objects, sidecar_errors = extract_sidecar_objects(path, paths)
        if not sidecar_errors:
            objects_here += sidecar_objects
    rel = display_path(path, paths.root)
    return (
        rel, stat.st_mtime_ns, stat.st_size, normalized_digest(path), path.suffix.lstrip("."),
        json.dumps(objects_here), clock.today(),
    ), rel


def _refs_for(path: Path, paths: ObjectLocations) -> list[tuple]:
    try:
        text = read_text(path)
    except OSError:
        return []
    rel = display_path(path, paths.root)
    return [(rel, ref, line) for line, ref in hydra_refs_by_line(path, text)]


def rebuild_documents_and_refs(conn: sqlite3.Connection, paths: ObjectLocations) -> int:
    """Full scan: every file a registered object form claims, read once.
    Only a first build or an explicit `ref store rebuild` pays this; ordinary
    freshness after that is `repair_stale_documents`'s per-file stat check."""
    conn.execute("DELETE FROM documents")
    conn.execute("DELETE FROM refs")
    count = 0
    for path in object_metadata_paths(paths):
        row, rel = _document_row(path, paths)
        conn.execute("INSERT OR REPLACE INTO documents VALUES (?, ?, ?, ?, ?, ?, ?)", row)
        for ref_row in _refs_for(path, paths):
            conn.execute("INSERT INTO refs VALUES (?, ?, ?)", ref_row)
        count += 1
    return count


def rebuild_store(paths: ObjectLocations, local: Path) -> int | None:
    """Full rebuild of every table. Returns the object count, or `None` if
    there is no export to build `objects`/`aliases`/`relations`/`provenance`
    from yet (run `ref index` first)."""
    digest = export_digest(paths)
    if digest is None:
        return None

    def _populate(conn: sqlite3.Connection) -> None:
        create_schema(conn)
        _populate_object_tables(conn, paths, digest)
        rebuild_documents_and_refs(conn, paths)
        conn.execute("INSERT OR REPLACE INTO meta VALUES ('built_at', ?)", (clock.today(),))

    rebuild_atomically(default_store_path(local), _populate)
    entries, _errors = registry_object_entries(paths.object_registry, paths.root)
    return len(entries)


def store_status(paths: ObjectLocations) -> str:
    db_path = default_store_path(paths.local)
    if not db_path.exists():
        return "missing"
    conn = connect_existing(db_path)
    if conn is None:
        return "stale"
    try:
        if not schema_matches(conn):
            return "stale"
        current_digest = export_digest(paths)
        if current_digest is None:
            return "fresh"
        return "fresh" if store_meta(conn).get("export_digest") == current_digest else "stale"
    finally:
        conn.close()


def repair_stale_documents(conn: sqlite3.Connection, paths: ObjectLocations, *, verify_digests: bool = False) -> int:
    """Re-read only the files that changed since the store's last build, or
    that are new; drop rows for files that no longer exist. This is the
    per-file freshness contract for `documents`/
    `refs`, and the reason those two tables avoid a scan on every read
    instead of only on the first one.

    Default: `(mtime_ns, size)` -- trusted only in the developer loop, where
    mtime is meaningful. `verify_digests=True` re-hashes each stored path
    instead, for a store restored across a machine boundary (a CI cache
    artifact) where mtime carries no information: every row's mtime differs
    from what was recorded, so the default path would treat every file as
    stale and re-read it, discarding the whole point of a restored cache.
    Comparing content digests instead recognizes the files that did not
    actually change despite the foreign mtime."""
    stored = {
        row[0]: (row[1], row[2], row[3])
        for row in conn.execute("SELECT path, mtime_ns, size, digest FROM documents")
    }
    seen: set[str] = set()
    repaired = 0
    for path in object_metadata_paths(paths):
        rel = display_path(path, paths.root)
        seen.add(rel)
        stat = path.stat()
        cached = stored.get(rel)
        if cached is not None:
            if verify_digests:
                if cached[2] == normalized_digest(path):
                    continue
            elif cached[:2] == (stat.st_mtime_ns, stat.st_size):
                continue
        row, _rel = _document_row(path, paths)
        conn.execute("INSERT OR REPLACE INTO documents VALUES (?, ?, ?, ?, ?, ?, ?)", row)
        conn.execute("DELETE FROM refs WHERE src_path = ?", (rel,))
        for ref_row in _refs_for(path, paths):
            conn.execute("INSERT INTO refs VALUES (?, ?, ?)", ref_row)
        repaired += 1
    for stale_path in set(stored) - seen:
        conn.execute("DELETE FROM documents WHERE path = ?", (stale_path,))
        conn.execute("DELETE FROM refs WHERE src_path = ?", (stale_path,))
        repaired += 1
    if repaired:
        conn.commit()
    return repaired
