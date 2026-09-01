"""Mirror test for `hydra_engine.objects.store_build`."""

from __future__ import annotations

import os
import sys
import tempfile
import unittest
from pathlib import Path

_SRC = Path(__file__).resolve().parents[3] / "src"
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

from hydra_engine.identity.schema_versions import CURRENT_SCHEMA_VERSION  # noqa: E402
from hydra_engine.objects import discovery, registry, store_build, store_schema  # noqa: E402
from hydra_engine.ports.sqlite_db import connect  # noqa: E402

UID = "11111111-1111-4111-8111-111111111111"


def _paths(root: Path) -> discovery.ObjectLocations:
    hydra = root / ".hydra-framework"
    return discovery.ObjectLocations(
        root=root, hydra=hydra, local=root / ".hydra-framework.local",
        personal_tasks_rel="tasks/personal", object_registry=hydra / "cognition/graph/registry.yaml",
    )


def _write(paths: discovery.ObjectLocations, rel: str, content: str) -> Path:
    path = paths.hydra / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    return path


def _object_file(paths: discovery.ObjectLocations, rel: str, hydra_id: str, *, relates_to: str = "", body: str = "# Test Object\nSee hydra://knowledge-unit/0002-other for context.\n") -> Path:
    relations = f"  - {relates_to}\n" if relates_to else ""
    return _write(
        paths, rel,
        "---\n"
        f"hydra_id: {hydra_id}\n"
        f"uid: {UID}\n"
        f"schema_version: {CURRENT_SCHEMA_VERSION}\n"
        "kind: knowledge-unit\n"
        "title: Test Object\n"
        "status: active\n"
        "scope: base-seed\n"
        "owners:\n"
        "  team: hydra\n"
        "relations:\n" + relations +
        "provenance:\n"
        "  sources: []\n"
        "---\n" + body,
    )


def _repo() -> discovery.ObjectLocations:
    root = Path(tempfile.mkdtemp(prefix="store-build-"))
    return _paths(root)


def _index(paths: discovery.ObjectLocations) -> None:
    objects, errors = discovery.collect_hydra_objects(paths)
    assert not errors, errors
    from hydra_engine.documents.tokens import write_text
    write_text(paths.object_registry, registry.object_registry_text(objects))


class ExportDigestTests(unittest.TestCase):
    def test_none_without_an_export(self):
        self.assertIsNone(store_build.export_digest(_repo()))

    def test_present_once_indexed(self):
        paths = _repo()
        _object_file(paths, "repo/knowledge-units/0001-a.md", "hydra://knowledge-unit/0001-a")
        _index(paths)
        self.assertIsNotNone(store_build.export_digest(paths))


class RebuildStoreTests(unittest.TestCase):
    def test_returns_none_without_an_export(self):
        paths = _repo()
        self.assertIsNone(store_build.rebuild_store(paths, paths.local))

    def test_populates_objects_aliases_relations_and_provenance(self):
        paths = _repo()
        _object_file(paths, "repo/knowledge-units/0001-a.md", "hydra://knowledge-unit/0001-a", relates_to="hydra://knowledge-unit/0002-other")
        _object_file(paths, "repo/knowledge-units/0002-other.md", "hydra://knowledge-unit/0002-other")
        _index(paths)

        count = store_build.rebuild_store(paths, paths.local)
        self.assertEqual(count, 2)

        conn = connect(store_schema.default_store_path(paths.local))
        self.assertTrue(store_schema.schema_matches(conn))
        ids = {row[0] for row in conn.execute("SELECT hydra_id FROM objects")}
        self.assertEqual(ids, {"hydra://knowledge-unit/0001-a", "hydra://knowledge-unit/0002-other"})
        relations = conn.execute(
            "SELECT dst_id FROM relations WHERE src_id = ?", ("hydra://knowledge-unit/0001-a",)
        ).fetchall()
        self.assertEqual([row[0] for row in relations], ["hydra://knowledge-unit/0002-other"])
        conn.close()

    def test_populates_documents_and_refs_from_a_full_scan(self):
        paths = _repo()
        _object_file(paths, "repo/knowledge-units/0001-a.md", "hydra://knowledge-unit/0001-a")
        _index(paths)

        store_build.rebuild_store(paths, paths.local)
        conn = connect(store_schema.default_store_path(paths.local))
        doc_paths = {row[0] for row in conn.execute("SELECT path FROM documents")}
        self.assertIn(".hydra-framework/repo/knowledge-units/0001-a.md", doc_paths)
        refs = conn.execute(
            "SELECT dst_ref, line FROM refs WHERE src_path = ?",
            (".hydra-framework/repo/knowledge-units/0001-a.md",),
        ).fetchall()
        ref_targets = {dst for dst, _line in refs}
        self.assertIn("hydra://knowledge-unit/0002-other", ref_targets)
        self.assertTrue(all(line > 0 for _dst, line in refs))
        conn.close()

    def test_export_digest_recorded_in_meta(self):
        paths = _repo()
        _object_file(paths, "repo/knowledge-units/0001-a.md", "hydra://knowledge-unit/0001-a")
        _index(paths)
        store_build.rebuild_store(paths, paths.local)
        conn = connect(store_schema.default_store_path(paths.local))
        self.assertEqual(store_schema.store_meta(conn)["export_digest"], store_build.export_digest(paths))
        conn.close()


class StoreStatusTests(unittest.TestCase):
    def test_reports_missing_before_first_build(self):
        self.assertEqual(store_build.store_status(_repo()), "missing")

    def test_reports_fresh_after_rebuild(self):
        paths = _repo()
        _object_file(paths, "repo/knowledge-units/0001-a.md", "hydra://knowledge-unit/0001-a")
        _index(paths)
        store_build.rebuild_store(paths, paths.local)
        self.assertEqual(store_build.store_status(paths), "fresh")

    def test_reports_stale_when_export_changes(self):
        paths = _repo()
        _object_file(paths, "repo/knowledge-units/0001-a.md", "hydra://knowledge-unit/0001-a")
        _index(paths)
        store_build.rebuild_store(paths, paths.local)
        _object_file(paths, "repo/knowledge-units/0002-a.md", "hydra://knowledge-unit/0002-a")
        _index(paths)
        self.assertEqual(store_build.store_status(paths), "stale")

    def test_reports_stale_for_invalid_sqlite_file(self):
        paths = _repo()
        db_path = store_schema.default_store_path(paths.local)
        db_path.parent.mkdir(parents=True)
        db_path.write_text("not sqlite", encoding="utf-8")
        self.assertEqual(store_build.store_status(paths), "stale")


class RepairStaleDocumentsTests(unittest.TestCase):
    def test_unchanged_file_needs_no_repair(self):
        paths = _repo()
        target = _object_file(paths, "repo/knowledge-units/0001-a.md", "hydra://knowledge-unit/0001-a")
        _index(paths)
        store_build.rebuild_store(paths, paths.local)

        conn = connect(store_schema.default_store_path(paths.local))
        repaired = store_build.repair_stale_documents(conn, paths)
        self.assertEqual(repaired, 0)
        conn.close()
        self.assertTrue(target.exists())

    def test_changed_file_is_reread_and_refs_updated(self):
        paths = _repo()
        target = _object_file(paths, "repo/knowledge-units/0001-a.md", "hydra://knowledge-unit/0001-a")
        _index(paths)
        store_build.rebuild_store(paths, paths.local)

        target.write_text(target.read_text(encoding="utf-8") + "\nAlso see hydra://knowledge-unit/0003-new.\n", encoding="utf-8")
        conn = connect(store_schema.default_store_path(paths.local))
        repaired = store_build.repair_stale_documents(conn, paths)
        self.assertEqual(repaired, 1)
        refs = {row[0] for row in conn.execute(
            "SELECT dst_ref FROM refs WHERE src_path = ?", (".hydra-framework/repo/knowledge-units/0001-a.md",)
        )}
        self.assertIn("hydra://knowledge-unit/0003-new", refs)
        conn.close()

    def test_deleted_file_drops_its_row(self):
        paths = _repo()
        target = _object_file(paths, "repo/knowledge-units/0001-a.md", "hydra://knowledge-unit/0001-a")
        _index(paths)
        store_build.rebuild_store(paths, paths.local)

        target.unlink()
        conn = connect(store_schema.default_store_path(paths.local))
        repaired = store_build.repair_stale_documents(conn, paths)
        self.assertEqual(repaired, 1)
        remaining = conn.execute(
            "SELECT COUNT(*) FROM documents WHERE path = ?", (".hydra-framework/repo/knowledge-units/0001-a.md",)
        ).fetchone()[0]
        self.assertEqual(remaining, 0)
        conn.close()

    def test_verify_digests_ignores_a_foreign_mtime_on_unchanged_content(self):
        """The cross-machine restore recipe: a store copied from
        another machine has `mtime_ns` values that mean nothing locally, so
        the default path (below) would re-read every file. `verify_digests`
        recognizes unchanged content instead."""
        paths = _repo()
        target = _object_file(paths, "repo/knowledge-units/0001-a.md", "hydra://knowledge-unit/0001-a")
        _index(paths)
        store_build.rebuild_store(paths, paths.local)

        os.utime(target, (target.stat().st_mtime + 1000, target.stat().st_mtime + 1000))
        conn = connect(store_schema.default_store_path(paths.local))
        repaired = store_build.repair_stale_documents(conn, paths, verify_digests=True)
        self.assertEqual(repaired, 0)
        conn.close()

    def test_default_mtime_path_rejects_every_row_on_a_foreign_mtime(self):
        paths = _repo()
        target = _object_file(paths, "repo/knowledge-units/0001-a.md", "hydra://knowledge-unit/0001-a")
        _index(paths)
        store_build.rebuild_store(paths, paths.local)

        os.utime(target, (target.stat().st_mtime + 1000, target.stat().st_mtime + 1000))
        conn = connect(store_schema.default_store_path(paths.local))
        repaired = store_build.repair_stale_documents(conn, paths)
        self.assertEqual(repaired, 1)
        conn.close()

    def test_verify_digests_still_catches_real_content_changes(self):
        paths = _repo()
        target = _object_file(paths, "repo/knowledge-units/0001-a.md", "hydra://knowledge-unit/0001-a")
        _index(paths)
        store_build.rebuild_store(paths, paths.local)

        target.write_text(target.read_text(encoding="utf-8") + "\nAlso see hydra://knowledge-unit/0003-new.\n", encoding="utf-8")
        conn = connect(store_schema.default_store_path(paths.local))
        repaired = store_build.repair_stale_documents(conn, paths, verify_digests=True)
        self.assertEqual(repaired, 1)
        conn.close()


if __name__ == "__main__":
    unittest.main()
