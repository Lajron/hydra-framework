"""Mirror test for `hydra_engine.work.task_store`."""

from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

_SRC = Path(__file__).resolve().parents[3] / "src"
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

from hydra_engine.objects.store_schema import create_schema  # noqa: E402
from hydra_engine.ports.sqlite_db import connect  # noqa: E402
from hydra_engine.work import task_store  # noqa: E402
from hydra_engine.work.paths import WorkPaths  # noqa: E402


def _paths() -> WorkPaths:
    root = Path(tempfile.mkdtemp(prefix="work-task-store-"))
    return WorkPaths(root=root, hydra=root / ".hydra-framework", local=root / ".hydra-framework.local")


def _seed_task(paths: WorkPaths, owner: str, *, status: str = "active", blocker: str = "") -> Path:
    path = paths.owner_task_dir(owner) / "2026-01-01-x.md"
    path.parent.mkdir(parents=True, exist_ok=True)
    blockers_section = f"## Blockers\n\n- {blocker}\n" if blocker else "## Blockers\n\n- None.\n"
    path.write_text(
        f"# Task: x\n\nStatus: {status}\nOwner: {owner}\nUpdated: 2026-01-01\n\n"
        f"## Goal\n\nx\n\n{blockers_section}", encoding="utf-8",
    )
    return path


def _store_conn(paths: WorkPaths):
    from hydra_engine.objects.store_schema import default_store_path
    conn = connect(default_store_path(paths.local))
    create_schema(conn)
    return conn


class RebuildTasksTests(unittest.TestCase):
    def test_populates_every_task_record(self):
        paths = _paths()
        _seed_task(paths, "dana")
        _seed_task(paths, "reed", status="blocked", blocker="waiting on review")
        conn = _store_conn(paths)
        count = task_store.rebuild_tasks(conn, paths)
        self.assertEqual(count, 2)
        rows = conn.execute("SELECT owner, status, blocked_on FROM tasks ORDER BY owner").fetchall()
        self.assertEqual(rows, [("dana", "active", "None."), ("reed", "blocked", "waiting on review")])
        conn.close()


class RepairStaleTasksTests(unittest.TestCase):
    def test_unchanged_record_needs_no_repair(self):
        paths = _paths()
        _seed_task(paths, "dana")
        conn = _store_conn(paths)
        task_store.rebuild_tasks(conn, paths)
        self.assertEqual(task_store.repair_stale_tasks(conn, paths), 0)
        conn.close()

    def test_changed_record_is_reread(self):
        paths = _paths()
        target = _seed_task(paths, "dana")
        conn = _store_conn(paths)
        task_store.rebuild_tasks(conn, paths)
        target.write_text(target.read_text(encoding="utf-8").replace("Status: active", "Status: blocked"), encoding="utf-8")
        self.assertEqual(task_store.repair_stale_tasks(conn, paths), 1)
        status = conn.execute("SELECT status FROM tasks WHERE owner = 'dana'").fetchone()[0]
        self.assertEqual(status, "blocked")
        conn.close()

    def test_completed_record_drops_its_row(self):
        paths = _paths()
        target = _seed_task(paths, "dana")
        conn = _store_conn(paths)
        task_store.rebuild_tasks(conn, paths)
        target.unlink()
        self.assertEqual(task_store.repair_stale_tasks(conn, paths), 1)
        self.assertEqual(conn.execute("SELECT COUNT(*) FROM tasks").fetchone()[0], 0)
        conn.close()


class OpenFreshTaskStoreTests(unittest.TestCase):
    def test_none_when_no_store_built(self):
        paths = _paths()
        self.assertIsNone(task_store.open_fresh_task_store(paths))

    def test_open_once_built(self):
        paths = _paths()
        _seed_task(paths, "dana")
        conn = _store_conn(paths)
        task_store.rebuild_tasks(conn, paths)
        conn.close()
        opened = task_store.open_fresh_task_store(paths)
        self.assertIsNotNone(opened)
        opened.close()

    def test_disabled_by_env_var(self):
        paths = _paths()
        conn = _store_conn(paths)
        conn.close()
        with mock.patch.dict("os.environ", {"HYDRA_QUERY_STORE": "off"}):
            self.assertIsNone(task_store.open_fresh_task_store(paths))


class BoardRowsFromStoreTests(unittest.TestCase):
    def test_owner_filter(self):
        paths = _paths()
        _seed_task(paths, "dana")
        _seed_task(paths, "reed")
        conn = _store_conn(paths)
        task_store.rebuild_tasks(conn, paths)
        rows = task_store.board_rows_from_store(conn, "dana", False, None)
        self.assertEqual([row["owner"] for row in rows], ["dana"])
        conn.close()

    def test_blocked_only(self):
        paths = _paths()
        _seed_task(paths, "dana")
        _seed_task(paths, "reed", status="blocked", blocker="waiting")
        conn = _store_conn(paths)
        task_store.rebuild_tasks(conn, paths)
        rows = task_store.board_rows_from_store(conn, None, True, None)
        self.assertEqual([row["owner"] for row in rows], ["reed"])
        conn.close()

    def test_stale_before(self):
        paths = _paths()
        _seed_task(paths, "dana")
        conn = _store_conn(paths)
        task_store.rebuild_tasks(conn, paths)
        self.assertEqual(task_store.board_rows_from_store(conn, None, False, "2025-01-01"), [])
        self.assertEqual(len(task_store.board_rows_from_store(conn, None, False, "2027-01-01")), 1)
        conn.close()


if __name__ == "__main__":
    unittest.main()
