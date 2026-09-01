"""Read queries over the operational object store.

`open_fresh_store` is the one place that decides a store is trustworthy
enough to answer from: schema-current and digest-matched to the current
export. Every query function takes an already-open connection rather than
opening one itself, so a caller that already paid `open_fresh_store`'s cost
once can run several queries against it; a caller that gets `None` back
degrades to the scan path and never calls these at all.

This module answers queries the flat export cannot without a full-tree scan
per query -- reverse references (`citers_of`) and transitive impact
(`impact`) -- which is what justifies these tables independent of how fast
scanning becomes.
"""

from __future__ import annotations

import sqlite3

from hydra_engine.objects.store_build import export_digest, store_status
from hydra_engine.objects.store_schema import default_store_path, schema_matches, store_meta
from hydra_engine.ports.sqlite_db import connect_existing, query_store_disabled

DEFAULT_IMPACT_DEPTH = 5


def open_fresh_store(paths, local) -> sqlite3.Connection | None:
    """An open connection only if the store is schema-current and its
    recorded export digest matches the export's current digest, else `None`.
    Every caller degrades to the scan path on `None`: a
    missing, stale, corrupt, or unusable store must never break a command.

    `HYDRA_QUERY_STORE=off` short-circuits to `None` before even trying to
    connect -- the one place every Stage 3 read query is gated on it."""
    if query_store_disabled():
        return None
    conn = connect_existing(default_store_path(local))
    if conn is None:
        return None
    if not schema_matches(conn):
        conn.close()
        return None
    digest = export_digest(paths)
    if digest is None or store_meta(conn).get("export_digest") != digest:
        conn.close()
        return None
    return conn


def _canonical_id(conn: sqlite3.Connection, ref: str) -> str | None:
    ref = ref.lower()
    row = conn.execute("SELECT hydra_id FROM objects WHERE hydra_id = ?", (ref,)).fetchone()
    if row:
        return row[0]
    row = conn.execute("SELECT hydra_id FROM aliases WHERE alias = ?", (ref,)).fetchone()
    return row[0] if row else None


def resolve(conn: sqlite3.Connection, ref: str) -> dict | None:
    """The object behind `ref` (a primary id or an alias), with its aliases,
    outbound relations, and provenance sources -- the same shape `ref
    resolve` prints, served from indexes instead of the O(n) scan-and-filter
    `commands/references.py`'s `command_ref_resolve` does today."""
    hydra_id = _canonical_id(conn, ref)
    if hydra_id is None:
        return None
    columns = ("hydra_id", "uid", "path", "digest", "family", "kind", "status", "tier", "scope", "schema_version", "title", "envelope_path")
    row = conn.execute(f"SELECT {', '.join(columns)} FROM objects WHERE hydra_id = ?", (hydra_id,)).fetchone()
    if row is None:
        return None
    obj = dict(zip(columns, row))
    obj["resolved_from_alias"] = ref if ref != hydra_id else ""
    obj["aliases"] = sorted(r[0] for r in conn.execute("SELECT alias FROM aliases WHERE hydra_id = ?", (hydra_id,)))
    obj["relations"] = sorted(r[0] for r in conn.execute("SELECT dst_id FROM relations WHERE src_id = ?", (hydra_id,)))
    obj["provenance_sources"] = sorted(r[0] for r in conn.execute("SELECT source_path FROM provenance WHERE hydra_id = ?", (hydra_id,)))
    return obj


def by_uid(conn: sqlite3.Connection, uid: str) -> list[dict]:
    return _rows(conn, "SELECT hydra_id, path FROM objects WHERE uid = ?", (uid,))


def by_path(conn: sqlite3.Connection, path: str) -> list[dict]:
    return _rows(conn, "SELECT hydra_id, path FROM objects WHERE path = ?", (path,))


def by_digest(conn: sqlite3.Connection, digest: str) -> list[dict]:
    return _rows(conn, "SELECT hydra_id, path FROM objects WHERE digest = ?", (digest,))


def _rows(conn: sqlite3.Connection, sql: str, params: tuple) -> list[dict]:
    return [{"hydra_id": row[0], "path": row[1]} for row in conn.execute(sql, params)]


def citers_of(conn: sqlite3.Connection, ref: str) -> list[str]:
    """Every object whose `relations` name `ref` -- absent from today's CLI
    entirely (`objects/references.py` only checks that a `hydra://` target
    resolves, in one direction); this is what `ref rdeps` serves."""
    hydra_id = _canonical_id(conn, ref)
    if hydra_id is None:
        return []
    return sorted(row[0] for row in conn.execute("SELECT DISTINCT src_id FROM relations WHERE dst_id = ?", (hydra_id,)))


def citers_of_source_path(conn: sqlite3.Connection, source_path: str) -> list[str]:
    """Every object whose `provenance.sources` names `source_path` verbatim
    -- the inverse of the forward `provenance_sources` list `resolve()`
    already returns per-object, the same relationship `citers_of` has to
    `relations`. `explain-path` is the one caller:
    a path need not be an object itself to be cited as another object's
    source material."""
    return sorted(row[0] for row in conn.execute("SELECT DISTINCT hydra_id FROM provenance WHERE source_path = ?", (source_path,)))


def impact(conn: sqlite3.Connection, ref: str, depth: int = DEFAULT_IMPACT_DEPTH) -> list[str]:
    """Every object transitively reachable from `ref` by outbound relations,
    within `depth` hops. A recursive CTE with a path-membership guard, so a
    relation cycle terminates instead of looping forever."""
    hydra_id = _canonical_id(conn, ref)
    if hydra_id is None:
        return []
    rows = conn.execute(
        """
        WITH RECURSIVE impact_walk(id, depth, path) AS (
            SELECT dst_id, 1, ',' || ? || ',' || dst_id || ','
            FROM relations WHERE src_id = ?
            UNION
            SELECT r.dst_id, impact_walk.depth + 1, impact_walk.path || r.dst_id || ','
            FROM relations r JOIN impact_walk ON r.src_id = impact_walk.id
            WHERE impact_walk.depth < ? AND impact_walk.path NOT LIKE '%,' || r.dst_id || ',%'
        )
        SELECT DISTINCT id FROM impact_walk
        """,
        (hydra_id, hydra_id, max(depth, 1)),
    ).fetchall()
    return sorted(row[0] for row in rows)
