"""Mirror test for `hydra_engine.work.board`."""

from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

_SRC = Path(__file__).resolve().parents[3] / "src"
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

from hydra_engine.work import board  # noqa: E402
from hydra_engine.work.paths import WorkPaths  # noqa: E402


def _paths() -> WorkPaths:
    root = Path(tempfile.mkdtemp(prefix="work-board-"))
    return WorkPaths(root=root, hydra=root / ".hydra-framework", local=root / ".hydra-framework.local")


def _seed_task(paths: WorkPaths, owner: str, status: str = "active", updated: str = "2026-01-01") -> Path:
    path = paths.owner_task_dir(owner) / "2026-01-01-x.md"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        f"# Task: x\n\nStatus: {status}\nOwner: {owner}\nUpdated: {updated}\n\n## Goal\n\nx\n", encoding="utf-8"
    )
    return path


class BoardRowsTests(unittest.TestCase):
    def test_returns_a_row_per_task(self) -> None:
        paths = _paths()
        _seed_task(paths, "dana")
        _seed_task(paths, "reed")
        rows = board.board_rows(paths)
        self.assertEqual({row["owner"] for row in rows}, {"dana", "reed"})

    def test_owner_filter_narrows_the_rows(self) -> None:
        paths = _paths()
        _seed_task(paths, "dana")
        _seed_task(paths, "reed")
        rows = board.board_rows(paths, "dana")
        self.assertEqual([row["owner"] for row in rows], ["dana"])

    def test_blocked_filter_narrows_the_rows(self) -> None:
        paths = _paths()
        _seed_task(paths, "dana")
        _seed_task(paths, "reed", status="blocked")
        rows = board.board_rows(paths, blocked_only=True)
        self.assertEqual([row["owner"] for row in rows], ["reed"])

    def test_stale_filter_narrows_the_rows(self) -> None:
        paths = _paths()
        _seed_task(paths, "dana", updated="2020-01-01")
        _seed_task(paths, "reed", updated="2026-08-20")
        with mock.patch("hydra_engine.ports.clock.today", return_value="2026-08-27"):
            rows = board.board_rows(paths, stale_days=14)
        self.assertEqual([row["owner"] for row in rows], ["dana"])

    def test_store_backed_rows_match_the_scan_path(self) -> None:
        """A fresh store and the scan fallback must agree, so
        `board`'s output cannot tell which one answered."""
        from hydra_engine.objects.store_schema import create_schema, default_store_path
        from hydra_engine.ports.sqlite_db import connect
        from hydra_engine.work import task_store

        paths = _paths()
        _seed_task(paths, "dana")
        _seed_task(paths, "reed", status="blocked")
        scanned = board.board_rows(paths)

        conn = connect(default_store_path(paths.local))
        create_schema(conn)
        task_store.rebuild_tasks(conn, paths)
        conn.close()

        stored = board.board_rows(paths)
        self.assertEqual(
            sorted(stored, key=lambda row: row["owner"]),
            sorted(scanned, key=lambda row: row["owner"]),
        )


class CheckpointCountsByOwnerTests(unittest.TestCase):
    def test_counts_checkpoints_per_owner(self) -> None:
        paths = _paths()
        checkpoint = paths.owner_task_dir("dana") / "checkpoints" / "2026-01-01-x-checkpoint.md"
        checkpoint.parent.mkdir(parents=True)
        checkpoint.write_text("x\n", encoding="utf-8")
        self.assertEqual(board.checkpoint_counts_by_owner(paths), {"dana": 1})


def _reflections_dir(paths: WorkPaths) -> Path:
    return paths.hydra / "evolution" / "reflections"


def _seed_reflection(paths: WorkPaths, name: str = "2026-08-01-example.md") -> Path:
    directory = _reflections_dir(paths)
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / name
    path.write_text("# example\n", encoding="utf-8")
    return path


class ReflectionPacketCountTests(unittest.TestCase):
    def test_absent_directory_counts_zero(self) -> None:
        paths = _paths()
        self.assertEqual(board.reflection_packet_count(_reflections_dir(paths)), 0)

    def test_readme_is_not_counted(self) -> None:
        paths = _paths()
        _seed_reflection(paths, "README.md")
        self.assertEqual(board.reflection_packet_count(_reflections_dir(paths)), 0)

    def test_packets_are_counted(self) -> None:
        paths = _paths()
        _seed_reflection(paths)
        self.assertEqual(board.reflection_packet_count(_reflections_dir(paths)), 1)


def _telemetry_packages_dir(paths: WorkPaths) -> Path:
    return paths.hydra / "repo" / "telemetry" / "packages"


def _seed_telemetry_package(paths: WorkPaths, name: str, status: str = "open") -> Path:
    directory = _telemetry_packages_dir(paths) / name
    directory.mkdir(parents=True, exist_ok=True)
    (directory / "overview.md").write_text(f"---\nstatus: {status}\n---\n# example\n", encoding="utf-8")
    return directory


class TelemetryEvidenceOpenCountTests(unittest.TestCase):
    def test_absent_directory_counts_zero(self) -> None:
        paths = _paths()
        self.assertEqual(board.telemetry_evidence_open_count(_telemetry_packages_dir(paths)), 0)

    def test_open_packages_are_counted(self) -> None:
        paths = _paths()
        _seed_telemetry_package(paths, "2026-08-01-dana-example")
        self.assertEqual(board.telemetry_evidence_open_count(_telemetry_packages_dir(paths)), 1)

    def test_terminal_packages_are_not_counted(self) -> None:
        paths = _paths()
        _seed_telemetry_package(paths, "2026-08-01-dana-example", status="absorbed")
        self.assertEqual(board.telemetry_evidence_open_count(_telemetry_packages_dir(paths)), 0)


class StatePointerLinesTests(unittest.TestCase):
    def test_unresolved_owner_is_silent(self) -> None:
        paths = _paths()
        self.assertEqual(board.state_pointer_lines(paths, "", "", _reflections_dir(paths)), [])

    def test_no_tasks_no_reflections_is_silent(self) -> None:
        paths = _paths()
        self.assertEqual(board.state_pointer_lines(paths, "dana", "", _reflections_dir(paths)), [])

    def test_owners_own_tasks_are_named(self) -> None:
        paths = _paths()
        _seed_task(paths, "dana")
        lines = board.state_pointer_lines(paths, "dana", "", _reflections_dir(paths))
        self.assertTrue(any("Yours (dana)" in line for line in lines))

    def test_teammates_tasks_are_counted_not_named(self) -> None:
        paths = _paths()
        _seed_task(paths, "reed")
        lines = board.state_pointer_lines(paths, "dana", "", _reflections_dir(paths))
        self.assertTrue(any("Teammates: 1 active record" in line for line in lines))

    def test_reflections_are_counted_when_no_tasks_are_in_flight(self) -> None:
        paths = _paths()
        _seed_reflection(paths)
        lines = board.state_pointer_lines(paths, "dana", "", _reflections_dir(paths))
        self.assertTrue(any("Reflections: 1 pending" in line for line in lines))

    def test_no_reflections_omits_the_line(self) -> None:
        paths = _paths()
        _seed_task(paths, "dana")
        lines = board.state_pointer_lines(paths, "dana", "", _reflections_dir(paths))
        self.assertFalse(any("Reflections:" in line for line in lines))

    def test_open_telemetry_evidence_is_counted(self) -> None:
        paths = _paths()
        _seed_telemetry_package(paths, "2026-08-01-dana-example")
        lines = board.state_pointer_lines(paths, "dana", "", _reflections_dir(paths), _telemetry_packages_dir(paths))
        self.assertTrue(any("Telemetry evidence: 1 open" in line for line in lines))

    def test_terminal_telemetry_evidence_omits_the_line(self) -> None:
        paths = _paths()
        _seed_telemetry_package(paths, "2026-08-01-dana-example", status="absorbed")
        lines = board.state_pointer_lines(paths, "dana", "", _reflections_dir(paths), _telemetry_packages_dir(paths))
        self.assertFalse(any("Telemetry evidence:" in line for line in lines))

    def test_no_telemetry_packages_dir_argument_is_backward_compatible(self) -> None:
        paths = _paths()
        _seed_task(paths, "dana")
        lines = board.state_pointer_lines(paths, "dana", "", _reflections_dir(paths))
        self.assertFalse(any("Telemetry evidence:" in line for line in lines))


if __name__ == "__main__":
    unittest.main()
