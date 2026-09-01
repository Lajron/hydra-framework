"""Mirror test for `hydra_engine.objects.envelopes`."""

from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

_SRC = Path(__file__).resolve().parents[3] / "src"
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

from hydra_engine.objects import envelopes  # noqa: E402
from hydra_engine.objects.discovery import ObjectLocations  # noqa: E402


def _paths(root: Path) -> ObjectLocations:
    hydra = root / ".hydra-framework"
    return ObjectLocations(
        root=root,
        hydra=hydra,
        local=root / ".hydra-framework.local",
        personal_tasks_rel="tasks/personal",
        object_registry=hydra / "cognition/graph/registry.yaml",
    )


class EnvelopeFieldTests(unittest.TestCase):
    def test_missing_envelope_fields_reports_every_gap(self):
        missing = envelopes.missing_envelope_fields({}, kind="", title="", status="", scope="")
        self.assertEqual(
            set(missing), {"kind", "title", "status", "scope", "owners", "relations", "provenance.sources"}
        )

    def test_empty_relations_and_sources_are_not_missing(self):
        data = {"relations": [], "provenance": {"sources": []}}
        missing = envelopes.missing_envelope_fields(data, kind="knowledge-unit", title="T", status="active", scope="repo")
        self.assertNotIn("relations", missing)
        self.assertNotIn("provenance.sources", missing)


class BuildHydraObjectTests(unittest.TestCase):
    def test_builds_an_object_from_frontmatter_style_data(self):
        root = Path(tempfile.mkdtemp(prefix="envelopes-test-"))
        hydra = root / ".hydra-framework"
        hydra.mkdir(parents=True)
        path = hydra / "obj.md"
        path.write_text("---\nhydra_id: hydra://knowledge-unit/0001-test\n---\n# Title\n", encoding="utf-8")
        data = {
            "hydra_id": "hydra://knowledge-unit/0001-test",
            "status": "active",
            "scope": "repo",
            "owners": {"example-owner": "2026-08-17"},
            "relations": [],
            "provenance": {"sources": []},
        }
        obj, error = envelopes.build_hydra_object(
            path, data, title="Title", kind="knowledge-unit", envelope_path=path, paths=_paths(root)
        )
        self.assertIsNone(error)
        self.assertEqual(obj["id"], "hydra://knowledge-unit/0001-test")
        self.assertEqual(obj["family"], "Knowledge")
        self.assertEqual(obj["tier"], "shared")

    def test_no_hydra_id_returns_none_without_error(self):
        root = Path(tempfile.mkdtemp(prefix="envelopes-test-"))
        path = root / ".hydra-framework" / "obj.md"
        path.parent.mkdir(parents=True)
        path.write_text("no id here\n", encoding="utf-8")
        obj, error = envelopes.build_hydra_object(
            path, {}, title="", kind="", envelope_path=path, paths=_paths(root)
        )
        self.assertIsNone(obj)
        self.assertIsNone(error)


class EnvelopeTextSurgeryTests(unittest.TestCase):
    def test_replace_envelope_field_rewrites_only_the_named_object(self):
        text = (
            "hydra_id: hydra://knowledge-unit/0001-test\n"
            "path: old/path.md\n"
            "---\n"
            "hydra_id: hydra://knowledge-unit/0002-test\n"
            "path: other/path.md\n"
        )
        updated, changed = envelopes.replace_envelope_field(text, "hydra://knowledge-unit/0001-test", "path", "new/path.md")
        self.assertTrue(changed)
        self.assertIn("path: new/path.md", updated)
        self.assertIn("path: other/path.md", updated)

    def test_replace_envelope_field_reports_no_change_for_unknown_object(self):
        text = "hydra_id: hydra://knowledge-unit/0001-test\npath: old/path.md\n"
        updated, changed = envelopes.replace_envelope_field(text, "hydra://knowledge-unit/9999-missing", "path", "x")
        self.assertFalse(changed)
        self.assertEqual(updated, text)

    def test_replace_envelope_field_ignores_a_same_named_field_nested_deeper(self):
        text = (
            "hydra_id: hydra://knowledge-unit/0001-test\n"
            "path: old/path.md\n"
            "provenance:\n"
            "  path: not-a-real-field\n"
        )
        updated, changed = envelopes.replace_envelope_field(text, "hydra://knowledge-unit/0001-test", "path", "new/path.md")
        self.assertTrue(changed)
        self.assertIn("path: new/path.md", updated)
        self.assertIn("  path: not-a-real-field", updated)


class ResolvedEnvelopePathTests(unittest.TestCase):
    def test_reverses_shared_tier_display_path(self):
        root = Path(tempfile.mkdtemp(prefix="envelopes-test-"))
        paths = _paths(root)
        resolved = envelopes.resolved_envelope_path(".hydra-framework/knowledge-units/0001.md", paths)
        self.assertEqual(resolved, paths.hydra / "knowledge-units/0001.md")

    def test_reverses_private_tier_display_path(self):
        root = Path(tempfile.mkdtemp(prefix="envelopes-test-"))
        paths = _paths(root)
        resolved = envelopes.resolved_envelope_path(".hydra-framework.local/notes.md", paths)
        self.assertEqual(resolved, paths.local / "notes.md")

    def test_reverses_external_display_path(self):
        root = Path(tempfile.mkdtemp(prefix="envelopes-test-"))
        paths = _paths(root)
        resolved = envelopes.resolved_envelope_path("repo/knowledge-units/0001.md", paths)
        self.assertEqual(resolved, paths.root / "repo/knowledge-units/0001.md")

    def test_round_trips_with_object_display_path(self):
        root = Path(tempfile.mkdtemp(prefix="envelopes-test-"))
        paths = _paths(root)
        original = paths.hydra / "knowledge-units/0001.md"
        display = envelopes.object_display_path(original, paths)
        self.assertEqual(envelopes.resolved_envelope_path(display, paths), original)


if __name__ == "__main__":
    unittest.main()
