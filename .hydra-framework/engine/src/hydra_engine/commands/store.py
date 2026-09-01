"""`ref store status`/`ref store rebuild`.

Registered from `commands/references.py`'s `ref` subparser rather than as
its own `COMMAND_MODULES` entry, the same way `objects/registry.py` supplies
logic to `commands/references.py` without being a command module itself --
`ref store ...` has to nest under the `ref` subparsers `register()` already
owns, and argparse subparsers cannot be shared across two `register()`
calls.

`command_ref_store_status` is the one disagreement detector: a
command, never a validator, so `validate`/`ref check` stay export-only.
"""

from __future__ import annotations

from hydra_engine.commands import CommandResult
from hydra_engine.documents.tokens import display_path
from hydra_engine.objects.store_build import export_digest, rebuild_store, repair_stale_documents, store_status
from hydra_engine.objects.store_schema import STORE_SCHEMA_VERSION, default_store_path, schema_matches, store_meta
from hydra_engine.ports.sqlite_db import connect, connect_existing
from hydra_engine.work import task_store
from hydra_engine.work.paths import WorkPaths

_TABLES = ("documents", "refs", "objects", "aliases", "relations", "provenance", "tasks")


def command_ref_store_status(paths) -> CommandResult:
    status = store_status(paths)
    db_path = default_store_path(paths.local)
    if not db_path.exists():
        print("Hydra ref store: not built. Run `hydra.py ref store rebuild`.")
        return CommandResult(0)

    conn = connect_existing(db_path)
    if conn is None:
        print(f"Hydra ref store: {display_path(db_path, paths.root)} exists but is not a valid SQLite database; treat as absent.")
        return CommandResult(0)

    if not schema_matches(conn):
        meta = store_meta(conn)
        print(f"Hydra ref store: schema mismatch (store: {meta.get('schema', '(none)')}, expected: {STORE_SCHEMA_VERSION}); rebuild required.")
        conn.close()
        return CommandResult(0)

    meta = store_meta(conn)
    current_digest = export_digest(paths)
    agreement = "no export to compare against" if current_digest is None else (
        "agrees with the export" if meta.get("export_digest") == current_digest else "STALE -- export changed since the last build; run `ref store rebuild`"
    )
    print(f"Hydra ref store: {display_path(db_path, paths.root)}")
    print(f"  status: {status}")
    print(f"  schema: {meta.get('schema', '(none)')}")
    print(f"  built: {meta.get('built_at', '(unknown)')}")
    print(f"  export digest: {agreement}")
    print(f"  size: {db_path.stat().st_size} bytes")
    for table in _TABLES:
        count = conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
        print(f"  {table}: {count} row(s)")
    conn.close()
    return CommandResult(0)


def command_ref_store_rebuild(args, paths) -> CommandResult:
    """`--verify-digests` is the CI cache-restore recipe: a
    store copied from another machine has a schema-current, export-digest-
    matching `objects`/`aliases`/`relations`/`provenance` (those are keyed to
    the export's content digest, not to any machine), but `documents`'
    `mtime_ns` values are foreign and would make every row look stale under
    the default developer-loop trust model. Re-hashing instead of a full
    rebuild recovers the store's value instead of discarding it. Without the
    flag, or when the store cannot be repaired in place (missing, schema-
    stale, or its export has actually changed), this is an unconditional full
    rebuild, unchanged from before this flag existed."""
    db_path = default_store_path(paths.local)
    if getattr(args, "if_exists", False) and not db_path.exists():
        return CommandResult(0)

    work_paths = WorkPaths(root=paths.root, hydra=paths.hydra, local=paths.local)

    if getattr(args, "verify_digests", False) and db_path.exists():
        conn = connect_existing(db_path)
        if conn is not None:
            current_digest = export_digest(paths)
            if schema_matches(conn) and current_digest is not None and store_meta(conn).get("export_digest") == current_digest:
                repaired = repair_stale_documents(conn, paths, verify_digests=True)
                task_repaired = task_store.repair_stale_tasks(conn, work_paths)
                conn.close()
                print(
                    f"Hydra ref store: repaired {repaired} document(s) and {task_repaired} task(s) "
                    f"at {display_path(db_path, paths.root)} (--verify-digests)"
                )
                return CommandResult(0)
            conn.close()

    count = rebuild_store(paths, paths.local)
    if count is None:
        print("Hydra ref store: no object registry to build from; run `hydra.py ref index` first.")
        return CommandResult(1)
    conn = connect(db_path)
    task_store.rebuild_tasks(conn, work_paths)
    conn.close()
    print(f"Hydra ref store: rebuilt from {count} object(s) at {display_path(db_path, paths.root)}")
    return CommandResult(0)
