"""Mirror test for `hydra_engine.commands.store`."""

from __future__ import annotations

import argparse
import contextlib
import io
import sys
import tempfile
import unittest
from pathlib import Path

_SRC = Path(__file__).resolve().parents[3] / "src"
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

from hydra_engine.commands import store  # noqa: E402
from hydra_engine.documents.tokens import write_text  # noqa: E402
from hydra_engine.objects import discovery, registry  # noqa: E402


def _paths() -> discovery.ObjectLocations:
    root = Path(tempfile.mkdtemp(prefix="commands-store-"))
    hydra = root / ".hydra-framework"
    hydra.mkdir(parents=True)
    return discovery.ObjectLocations(
        root=root, hydra=hydra, local=root / ".hydra-framework.local",
        personal_tasks_rel="tasks/personal", object_registry=hydra / "cognition/graph/registry.yaml",
    )


def _write_object(paths: discovery.ObjectLocations, rel: str, hydra_id: str) -> None:
    path = paths.hydra / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "---\n"
        f"hydra_id: {hydra_id}\n"
        "uid: 11111111-1111-4111-8111-111111111111\n"
        "schema_version: 3\n"
        "kind: knowledge-unit\ntitle: Fixture\nstatus: active\nscope: repo\n"
        "owners:\n  team: fixture\n"
        "relations: []\nprovenance:\n  sources: []\n"
        "---\n# Fixture\n",
        encoding="utf-8",
    )


def _index(paths: discovery.ObjectLocations) -> None:
    objects, errors = discovery.collect_hydra_objects(paths)
    assert not errors, errors
    write_text(paths.object_registry, registry.object_registry_text(objects))


class CommandRefStoreStatusTests(unittest.TestCase):
    def test_reports_not_built_when_absent(self):
        paths = _paths()
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            result = store.command_ref_store_status(paths)
        self.assertEqual(result.exit_code, 0)
        self.assertIn("not built", out.getvalue())

    def test_reports_agreement_and_row_counts_once_built(self):
        paths = _paths()
        _write_object(paths, "knowledge-units/0001.md", "hydra://knowledge-unit/0001-fixture")
        _index(paths)
        store.command_ref_store_rebuild(argparse.Namespace(if_exists=False), paths)

        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            result = store.command_ref_store_status(paths)
        self.assertEqual(result.exit_code, 0)
        text = out.getvalue()
        self.assertIn("agrees with the export", text)
        self.assertIn("objects: 1 row(s)", text)

    def test_reports_stale_when_export_changed_since_the_build(self):
        paths = _paths()
        _write_object(paths, "knowledge-units/0001.md", "hydra://knowledge-unit/0001-fixture")
        _index(paths)
        store.command_ref_store_rebuild(argparse.Namespace(if_exists=False), paths)

        _write_object(paths, "knowledge-units/0002.md", "hydra://knowledge-unit/0002-fixture")
        _index(paths)

        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            store.command_ref_store_status(paths)
        self.assertIn("STALE", out.getvalue())


class CommandRefStoreRebuildTests(unittest.TestCase):
    def test_refuses_without_an_export(self):
        paths = _paths()
        err = io.StringIO()
        with contextlib.redirect_stdout(err):
            result = store.command_ref_store_rebuild(argparse.Namespace(if_exists=False), paths)
        self.assertEqual(result.exit_code, 1)
        self.assertIn("ref index", err.getvalue())

    def test_builds_the_store(self):
        paths = _paths()
        _write_object(paths, "knowledge-units/0001.md", "hydra://knowledge-unit/0001-fixture")
        _index(paths)
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            result = store.command_ref_store_rebuild(argparse.Namespace(if_exists=False), paths)
        self.assertEqual(result.exit_code, 0)
        self.assertIn("rebuilt from 1 object(s)", out.getvalue())

    def test_if_exists_skips_a_first_build(self):
        paths = _paths()
        _write_object(paths, "knowledge-units/0001.md", "hydra://knowledge-unit/0001-fixture")
        _index(paths)
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            result = store.command_ref_store_rebuild(argparse.Namespace(if_exists=True), paths)
        self.assertEqual(result.exit_code, 0)
        self.assertEqual(out.getvalue(), "")

    def test_if_exists_still_rebuilds_once_a_store_exists(self):
        paths = _paths()
        _write_object(paths, "knowledge-units/0001.md", "hydra://knowledge-unit/0001-fixture")
        _index(paths)
        store.command_ref_store_rebuild(argparse.Namespace(if_exists=False), paths)

        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            result = store.command_ref_store_rebuild(argparse.Namespace(if_exists=True), paths)
        self.assertEqual(result.exit_code, 0)
        self.assertIn("rebuilt from 1 object(s)", out.getvalue())

    def test_rebuild_also_populates_the_tasks_table(self):
        paths = _paths()
        _write_object(paths, "knowledge-units/0001.md", "hydra://knowledge-unit/0001-fixture")
        _index(paths)
        task = paths.hydra / "tasks/personal/dana/2026-01-01-x.md"
        task.parent.mkdir(parents=True)
        task.write_text("Status: active\nOwner: dana\nUpdated: 2026-01-01\n\n## Goal\n\nx\n", encoding="utf-8")

        store.command_ref_store_rebuild(argparse.Namespace(if_exists=False), paths)

        from hydra_engine.ports.sqlite_db import connect_existing
        from hydra_engine.objects.store_schema import default_store_path
        conn = connect_existing(default_store_path(paths.local))
        rows = conn.execute("SELECT owner FROM tasks").fetchall()
        conn.close()
        self.assertEqual(rows, [("dana",)])


class CommandRefStoreRebuildVerifyDigestsTests(unittest.TestCase):
    def test_repairs_in_place_instead_of_a_full_rebuild(self):
        """The CI cache-restore recipe: a schema-current,
        export-digest-matching store gets its `documents`/`tasks` repaired
        by content digest in place, rather than a full teardown-rebuild."""
        paths = _paths()
        _write_object(paths, "knowledge-units/0001.md", "hydra://knowledge-unit/0001-fixture")
        target = paths.hydra / "knowledge-units/0001.md"
        _index(paths)
        store.command_ref_store_rebuild(argparse.Namespace(if_exists=False), paths)

        import os
        os.utime(target, (target.stat().st_mtime + 1000, target.stat().st_mtime + 1000))

        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            result = store.command_ref_store_rebuild(argparse.Namespace(if_exists=False, verify_digests=True), paths)
        self.assertEqual(result.exit_code, 0)
        self.assertIn("repaired", out.getvalue())
        self.assertIn("--verify-digests", out.getvalue())

    def test_falls_back_to_a_full_rebuild_without_an_existing_store(self):
        paths = _paths()
        _write_object(paths, "knowledge-units/0001.md", "hydra://knowledge-unit/0001-fixture")
        _index(paths)
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            result = store.command_ref_store_rebuild(argparse.Namespace(if_exists=False, verify_digests=True), paths)
        self.assertEqual(result.exit_code, 0)
        self.assertIn("rebuilt from 1 object(s)", out.getvalue())

    def test_falls_back_to_a_full_rebuild_when_the_export_has_actually_changed(self):
        paths = _paths()
        _write_object(paths, "knowledge-units/0001.md", "hydra://knowledge-unit/0001-fixture")
        _index(paths)
        store.command_ref_store_rebuild(argparse.Namespace(if_exists=False), paths)

        _write_object(paths, "knowledge-units/0002.md", "hydra://knowledge-unit/0002-fixture")
        _index(paths)

        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            result = store.command_ref_store_rebuild(argparse.Namespace(if_exists=False, verify_digests=True), paths)
        self.assertEqual(result.exit_code, 0)
        self.assertIn("rebuilt from 2 object(s)", out.getvalue())


if __name__ == "__main__":
    unittest.main()
