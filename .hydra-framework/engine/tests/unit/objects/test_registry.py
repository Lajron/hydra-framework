"""Mirror test for `hydra_engine.objects.registry`."""

from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

_SRC = Path(__file__).resolve().parents[3] / "src"
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

from hydra_engine.identity.schema_versions import CURRENT_SCHEMA_VERSION  # noqa: E402
from hydra_engine.objects import discovery, registry  # noqa: E402

UID = "11111111-1111-4111-8111-111111111111"


def _paths(root: Path) -> discovery.ObjectLocations:
    hydra = root / ".hydra-framework"
    return discovery.ObjectLocations(
        root=root,
        hydra=hydra,
        local=root / ".hydra-framework.local",
        personal_tasks_rel="tasks/personal",
        object_registry=hydra / "cognition/graph/registry.yaml",
    )


def _write(paths: discovery.ObjectLocations, rel: str, content: str) -> Path:
    path = paths.hydra / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    return path


def _object_file(paths: discovery.ObjectLocations, rel: str, hydra_id: str, *, uid: str | None = UID, body: str = "# Test Object\n") -> Path:
    uid_line = f"uid: {uid}\n" if uid else ""
    return _write(
        paths, rel,
        "---\n"
        f"hydra_id: {hydra_id}\n"
        f"{uid_line}"
        f"schema_version: {CURRENT_SCHEMA_VERSION}\n"
        "kind: knowledge-unit\n"
        "title: Test Object\n"
        "status: active\n"
        "scope: base-seed\n"
        "owners:\n"
        "  team: hydra\n"
        "relations:\n"
        "provenance:\n"
        "  sources: []\n"
        "---\n" + body,
    )


class ObjectRegistryTextTests(unittest.TestCase):
    def test_writes_derived_registry_entry(self):
        obj = {
            "id": "hydra://knowledge-unit/0001-test",
            "uid": "abc",
            "path": ".hydra-framework/obj.md",
            "digest": "sha256:aaa",
            "family": "Knowledge",
            "kind": "knowledge-unit",
            "status": "active",
            "tier": "shared",
            "scope": "repo",
            "schema_version": 3,
            "title": "Title",
            "aliases": [],
            "envelope_path": ".hydra-framework/obj.md",
            "relations": [],
            "provenance_sources": [],
        }
        text = registry.object_registry_text([obj])
        self.assertIn("schema: hydra-framework.object-registry.v1", text)
        self.assertIn("hydra://knowledge-unit/0001-test:", text)
        self.assertIn("uid: abc", text)
        # B1: a timestamp on every regeneration guaranteed a merge conflict
        # regardless of what else two branches changed; dropped entirely.
        self.assertNotIn("generated_at", text)
        self.assertNotIn("generated_by", text)


class RegistryObjectEntriesTests(unittest.TestCase):
    def test_round_trips_a_written_registry(self):
        root = Path(tempfile.mkdtemp(prefix="registry-test-"))
        obj = {
            "id": "hydra://knowledge-unit/0001-test",
            "uid": "",
            "path": ".hydra-framework/obj.md",
            "digest": "sha256:aaa",
            "family": "Knowledge",
            "kind": "knowledge-unit",
            "status": "active",
            "tier": "shared",
            "scope": "repo",
            "schema_version": 3,
            "title": "Title",
            "aliases": ["hydra://knowledge-unit/alt"],
            "envelope_path": ".hydra-framework/obj.md",
            "relations": [],
            "provenance_sources": [],
        }
        text = registry.object_registry_text([obj])
        path = root / "registry.yaml"
        path.write_text(text, encoding="utf-8")
        entries, errors = registry.registry_object_entries(path, root)
        self.assertEqual(errors, [])
        self.assertIn("hydra://knowledge-unit/0001-test", entries)
        self.assertEqual(entries["hydra://knowledge-unit/0001-test"]["aliases"], ["hydra://knowledge-unit/alt"])

    def test_missing_schema_is_reported(self):
        root = Path(tempfile.mkdtemp(prefix="registry-test-"))
        path = root / "not-a-registry.yaml"
        path.write_text("just: text\n", encoding="utf-8")
        entries, errors = registry.registry_object_entries(path, root)
        self.assertEqual(entries, {})
        self.assertTrue(errors)


class ValidateObjectRegistryFreshnessTests(unittest.TestCase):
    def test_absent_registry_is_valid(self):
        root = Path(tempfile.mkdtemp(prefix="registry-test-"))
        self.assertEqual(registry.validate_object_registry_freshness(_paths(root)), [])

    def test_missing_object_finding_carries_the_registry_as_its_path(self):
        root = Path(tempfile.mkdtemp(prefix="registry-test-"))
        paths = _paths(root)
        paths.hydra.mkdir(parents=True, exist_ok=True)
        (paths.hydra / "obj.md").write_text(
            "---\nhydra_id: hydra://knowledge-unit/0001-test\nuid: abc\nschema_version: 3\ntitle: Title\n"
            "status: active\nscope: repo\nowners:\n  team: fixture\nrelations: []\n"
            "provenance:\n  sources: []\n---\n# Title\n",
            encoding="utf-8",
        )
        paths.object_registry.parent.mkdir(parents=True, exist_ok=True)
        paths.object_registry.write_text(registry.object_registry_text([]), encoding="utf-8")
        findings = registry.validate_object_registry_freshness(paths)
        missing = [f for f in findings if "is missing object" in f.detail]
        self.assertEqual(len(missing), 1)
        self.assertEqual(missing[0].code, "object-registry-freshness")
        self.assertEqual(missing[0].path, ".hydra-framework/cognition/graph/registry.yaml")

    def test_reports_stale_digest_when_the_object_changed_in_place(self):
        # Moved from `test_hydra.py`'s `ObjectReferenceTests`: a real edit at the same path, not a move.
        root = Path(tempfile.mkdtemp(prefix="registry-test-"))
        paths = _paths(root)
        path = _object_file(paths, "knowledge-units/0001-test.md", "hydra://knowledge-unit/0001-test")
        registry.write_object_registry(paths)
        path.write_text(path.read_text(encoding="utf-8") + "\nChanged.\n", encoding="utf-8")

        errors = [str(e) for e in registry.validate_object_registry_freshness(paths)]
        self.assertTrue(any(
            "stale digest for `hydra://knowledge-unit/0001-test`" in e and "rerun `hydra.py ref index`" in e
            for e in errors
        ), errors)

    def test_reports_stale_aliases_with_a_rerun_hint(self):
        root = Path(tempfile.mkdtemp(prefix="registry-test-"))
        paths = _paths(root)
        _object_file(paths, "knowledge-units/0001-test.md", "hydra://knowledge-unit/0001-test")
        registry.write_object_registry(paths)
        registry_text = paths.object_registry.read_text(encoding="utf-8")
        registry_text = registry_text.replace("aliases: []", "aliases:\n      - hydra://knowledge-unit/legacy-name")
        paths.object_registry.write_text(registry_text, encoding="utf-8")

        errors = [str(e) for e in registry.validate_object_registry_freshness(paths)]
        self.assertTrue(any(
            "stale aliases for `hydra://knowledge-unit/0001-test`" in e and "rerun `hydra.py ref index`" in e
            for e in errors
        ), errors)

    def test_reports_ambiguous_move_when_neither_side_has_a_uid(self):
        # Moved from `test_hydra.py`'s `ObjectReferenceTests`: with no uid on this object, a matching
        # digest at a new path is a possible move, not a proven one.
        root = Path(tempfile.mkdtemp(prefix="registry-test-"))
        paths = _paths(root)
        original = _object_file(paths, "knowledge-units/0001-test.md", "hydra://knowledge-unit/0001-test", uid=None)
        registry.write_object_registry(paths)
        moved = paths.hydra / "knowledge-units/moved/0001-test.md"
        moved.parent.mkdir(parents=True, exist_ok=True)
        original.rename(moved)

        errors = [str(e) for e in registry.validate_object_registry_freshness(paths)]
        self.assertTrue(any("ambiguous: no uid on one or both sides" in e for e in errors), errors)


class WriteObjectRegistryTests(unittest.TestCase):
    def test_writes_and_counts_objects(self):
        root = Path(tempfile.mkdtemp(prefix="registry-test-"))
        hydra = root / ".hydra-framework"
        hydra.mkdir(parents=True)
        (hydra / "knowledge-units").mkdir()
        (hydra / "knowledge-units/0001.md").write_text(
            "---\nhydra_id: hydra://knowledge-unit/0001-test\nuid: abc\nschema_version: 3\ntitle: Fixture\n"
            "status: active\nscope: repo\nowners:\n  team: fixture\nrelations: []\nprovenance:\n  sources: []\n"
            "---\n# Fixture\n",
            encoding="utf-8",
        )
        paths = _paths(root)
        count = registry.write_object_registry(paths)
        self.assertEqual(count, 1)
        self.assertTrue(paths.object_registry.exists())
        self.assertIn("hydra://knowledge-unit/0001-test:", paths.object_registry.read_text(encoding="utf-8"))

    def test_refuses_to_write_when_discovery_reports_errors(self):
        # B3: a concurrent atomic replace mid-scan can make discovery report
        # a transient error; writing whatever partial object list came back
        # would corrupt the registry, so refuse and leave it untouched.
        root = Path(tempfile.mkdtemp(prefix="registry-test-"))
        paths = _paths(root)
        _object_file(paths, "knowledge-units/0001-test.md", "hydra://knowledge-unit/0001-test")
        registry.write_object_registry(paths)
        before = paths.object_registry.read_text(encoding="utf-8")

        _write(paths, "knowledge-units/0002-bad.md", "---\nbody: |\n  block scalar\n---\n")
        count = registry.write_object_registry(paths)

        self.assertIsNone(count)
        self.assertEqual(paths.object_registry.read_text(encoding="utf-8"), before)


class MoveDetectionFreshnessTests(unittest.TestCase):
    """`validate_object_registry_freshness`'s move-detection branches, moved
    from `test_hydra.py`'s `ObjectMoveTests`."""

    def test_registry_exports_uid(self):
        root = Path(tempfile.mkdtemp(prefix="registry-test-"))
        paths = _paths(root)
        _object_file(paths, "knowledge-units/0001-test.md", "hydra://knowledge-unit/0001-test")
        registry.write_object_registry(paths)
        self.assertIn(f"uid: {UID}", paths.object_registry.read_text(encoding="utf-8"))

    def test_manual_move_of_uid_carrying_object_is_unambiguous(self):
        root = Path(tempfile.mkdtemp(prefix="registry-test-"))
        paths = _paths(root)
        path = _object_file(paths, "knowledge-units/0001-test.md", "hydra://knowledge-unit/0001-test")
        registry.write_object_registry(paths)
        moved = paths.hydra / "knowledge-units/moved/0001-test.md"
        moved.parent.mkdir(parents=True, exist_ok=True)
        path.rename(moved)

        errors = [str(e) for e in registry.validate_object_registry_freshness(paths)]
        self.assertTrue(any("unambiguous move: same uid, same digest" in e for e in errors))
        self.assertTrue(any("rerun `hydra.py ref index`" in e for e in errors))

    def test_manual_move_with_an_edit_is_ambiguous(self):
        root = Path(tempfile.mkdtemp(prefix="registry-test-"))
        paths = _paths(root)
        path = _object_file(paths, "knowledge-units/0001-test.md", "hydra://knowledge-unit/0001-test")
        registry.write_object_registry(paths)
        moved = paths.hydra / "knowledge-units/moved/0001-test.md"
        moved.parent.mkdir(parents=True, exist_ok=True)
        path.rename(moved)
        moved.write_text(moved.read_text(encoding="utf-8") + "\nEdited.\n", encoding="utf-8")

        errors = [str(e) for e in registry.validate_object_registry_freshness(paths)]
        self.assertTrue(any("ambiguous: the digest changed" in e for e in errors))
        self.assertTrue(any("decide this by hand" in e for e in errors))

    def test_something_left_at_the_old_path_is_ambiguous(self):
        root = Path(tempfile.mkdtemp(prefix="registry-test-"))
        paths = _paths(root)
        path = _object_file(paths, "knowledge-units/0001-test.md", "hydra://knowledge-unit/0001-test")
        registry.write_object_registry(paths)
        moved = paths.hydra / "knowledge-units/moved/0001-test.md"
        moved.parent.mkdir(parents=True, exist_ok=True)
        path.rename(moved)
        # Same uid, same digest, new path -- but the old path is not empty, so
        # this reads as a copy and the resolver must not pick a winner.
        _write(paths, "knowledge-units/0001-test.md", "# Placeholder\n")

        errors = [str(e) for e in registry.validate_object_registry_freshness(paths)]
        self.assertTrue(any("a file still sits at the recorded path" in e for e in errors), errors)

    def test_renamed_hydra_id_is_repaired_through_uid(self):
        """The uid fallback: the readable ID changed, so only uid pairs these."""
        root = Path(tempfile.mkdtemp(prefix="registry-test-"))
        paths = _paths(root)
        _write(paths, "knowledge/notes.md", "# Notes\n")
        sidecar = _write(
            paths, "object-sidecars.yaml",
            "schema: hydra-framework.object-sidecar.v1\n"
            "objects:\n"
            "  notes:\n"
            "    hydra_id: hydra://knowledge-slice/notes\n"
            f"    uid: {UID}\n"
            f"    schema_version: {CURRENT_SCHEMA_VERSION}\n"
            "    kind: knowledge-slice\n"
            "    title: Notes\n"
            "    status: active\n"
            "    scope: base-seed\n"
            "    owners:\n"
            "      team: hydra\n"
            "    relations: []\n"
            "    path: .hydra-framework/knowledge/notes.md\n"
            "    provenance:\n"
            "      sources: []\n",
        )
        registry.write_object_registry(paths)

        moved = paths.hydra / "knowledge/archive/notes.md"
        moved.parent.mkdir(parents=True, exist_ok=True)
        (paths.hydra / "knowledge/notes.md").rename(moved)
        sidecar.write_text(
            sidecar.read_text(encoding="utf-8")
            .replace("hydra://knowledge-slice/notes", "hydra://knowledge-slice/archived-notes")
            .replace("path: .hydra-framework/knowledge/notes.md", "path: .hydra-framework/knowledge/archive/notes.md"),
            encoding="utf-8",
        )

        errors = [str(e) for e in registry.validate_object_registry_freshness(paths)]
        self.assertTrue(
            any("unambiguous move to `hydra://knowledge-slice/archived-notes`" in e for e in errors),
            errors,
        )

    def test_deleted_object_is_not_reported_as_a_move(self):
        root = Path(tempfile.mkdtemp(prefix="registry-test-"))
        paths = _paths(root)
        path = _object_file(paths, "knowledge-units/0001-test.md", "hydra://knowledge-unit/0001-test")
        registry.write_object_registry(paths)
        path.unlink()

        errors = registry.validate_object_registry_freshness(paths)
        self.assertTrue(any(str(e).endswith("has stale object `hydra://knowledge-unit/0001-test`") for e in errors))
        self.assertFalse(any("unambiguous move" in str(e) or "possible move" in str(e) for e in errors))


if __name__ == "__main__":
    unittest.main()
