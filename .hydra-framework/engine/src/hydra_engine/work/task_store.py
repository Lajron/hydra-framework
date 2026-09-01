"""Task-record table build and board queries over the operational store.

Layer 2, deliberately separate from `objects/store_build.py` (layer 1):
task records are `work/` state, not object-graph state, and layer direction
forbids a layer-1 module importing anything under `work/`. `commands/store.py`
composes both after a rebuild; `work/board.py` reads through here with the
scan as the fallback -- the same split the module table
specifies ("keeps task data out of layer 1").

Unlike `objects/store_queries.py`'s `open_fresh_store`, there is no export
digest to check here: task records are not derived from the object registry
export at all, so schema currency plus the same per-file `(mtime_ns, size)`
contract `objects/store_build.py` uses for `documents`/`refs` is the whole
freshness story for `tasks`.
"""

from __future__ import annotations

import sqlite3
from pathlib import Path

from hydra_engine.documents.tokens import display_path, read_text
from hydra_engine.objects.store_schema import default_store_path, schema_matches
from hydra_engine.ports.sqlite_db import connect_existing, query_store_disabled
from hydra_engine.work.paths import WorkPaths
from hydra_engine.work.task_records import iter_personal_task_files, task_header_field, task_name_from_path


def _first_nonblank_line_after(text: str, heading: str) -> str:
    """The `## Goal` section is prose; `## Blockers` is a bullet list (see
    `tasks/templates/task.md`) -- stripping a leading `- ` handles both."""
    for line in text.partition(heading)[2].splitlines():
        stripped = line.strip()
        if stripped:
            return stripped.removeprefix("- ")
    return ""


def task_row(path: Path, root: Path) -> tuple:
    text = read_text(path)
    stat = path.stat()
    return (
        display_path(path, root),
        path.parent.name,
        task_name_from_path(path),
        task_header_field(text, "Status") or "unknown",
        task_header_field(text, "Updated") or task_header_field(text, "Created"),
        _first_nonblank_line_after(text, "## Goal"),
        _first_nonblank_line_after(text, "## Blockers"),
        stat.st_mtime_ns,
        stat.st_size,
    )


def rebuild_tasks(conn: sqlite3.Connection, paths: WorkPaths) -> int:
    """Full rebuild of the `tasks` table: the one-time cost `ref store
    rebuild` pays right after building the rest of the store. Ordinary
    freshness after that is `repair_stale_tasks`'s per-file check."""
    conn.execute("DELETE FROM tasks")
    count = 0
    for path in iter_personal_task_files(paths):
        conn.execute("INSERT OR REPLACE INTO tasks VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)", task_row(path, paths.root))
        count += 1
    conn.commit()
    return count


def repair_stale_tasks(conn: sqlite3.Connection, paths: WorkPaths) -> int:
    """Re-read only task records whose `(mtime_ns, size)` changed since the
    store's last build, or that are new; drop rows for records that were
    completed or handed off elsewhere. Mirrors
    `objects.store_build.repair_stale_documents`'s per-file contract,
    applied to task records instead of canonical objects."""
    stored = {row[0]: (row[1], row[2]) for row in conn.execute("SELECT path, mtime_ns, size FROM tasks")}
    seen: set[str] = set()
    repaired = 0
    for path in iter_personal_task_files(paths):
        rel = display_path(path, paths.root)
        seen.add(rel)
        stat = path.stat()
        if stored.get(rel) == (stat.st_mtime_ns, stat.st_size):
            continue
        conn.execute("INSERT OR REPLACE INTO tasks VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)", task_row(path, paths.root))
        repaired += 1
    for stale_path in set(stored) - seen:
        conn.execute("DELETE FROM tasks WHERE path = ?", (stale_path,))
        repaired += 1
    if repaired:
        conn.commit()
    return repaired


def open_fresh_task_store(paths: WorkPaths) -> sqlite3.Connection | None:
    """An open, current connection to the `tasks` table, or `None` if the
    store is absent, schema-stale, disabled, or a repair write fails --
    every caller degrades to the scan path: a missing,
    stale, corrupt, or unusable store must never break a command."""
    if query_store_disabled():
        return None
    conn = connect_existing(default_store_path(paths.local))
    if conn is None:
        return None
    if not schema_matches(conn):
        conn.close()
        return None
    try:
        repair_stale_tasks(conn, paths)
    except sqlite3.Error:
        conn.close()
        return None
    return conn


def board_rows_from_store(
    conn: sqlite3.Connection,
    owner_filter: str | None,
    blocked_only: bool,
    stale_before: str | None,
) -> list[dict[str, str]]:
    """Row shape matches `work.task_records.task_summary` exactly (`owner`,
    `path`, `name`, `status`, `updated`, `goal`), so board rendering cannot
    tell which source produced it."""
    sql = "SELECT path, owner, name, status, updated, goal FROM tasks"
    clauses: list[str] = []
    params: list[str] = []
    if owner_filter:
        clauses.append("owner = ?")
        params.append(owner_filter)
    if blocked_only:
        clauses.append("status = 'blocked'")
    if stale_before is not None:
        clauses.append("updated != '' AND updated < ?")
        params.append(stale_before)
    if clauses:
        sql += " WHERE " + " AND ".join(clauses)
    rows = conn.execute(sql, params).fetchall()
    return [
        {"owner": owner, "path": path, "name": name, "status": status, "updated": updated, "goal": goal}
        for path, owner, name, status, updated, goal in rows
    ]
