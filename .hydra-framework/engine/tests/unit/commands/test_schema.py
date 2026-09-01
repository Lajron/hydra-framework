"""Mirror test for `hydra_engine.commands.schema`."""

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

from hydra_engine.commands import schema  # noqa: E402
from hydra_engine.objects import references  # noqa: E402
from hydra_engine.objects.discovery import ObjectLocations  # noqa: E402


def _paths() -> ObjectLocations:
    root = Path(tempfile.mkdtemp(prefix="commands-schema-"))
    hydra = root / ".hydra-framework"
    hydra.mkdir(parents=True)
    return ObjectLocations(
        root=root,
        hydra=hydra,
        local=root / ".hydra-framework.local",
        personal_tasks_rel="tasks/personal",
        object_registry=hydra / "cognition/graph/registry.yaml",
    )


def _write(paths: ObjectLocations, rel: str, content: str) -> Path:
    path = paths.hydra / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    return path


class CommandSchemaUpgradeTests(unittest.TestCase):
    def test_no_objects_reports_zero_upgraded(self):
        paths = _paths()
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            result = schema.command_schema_upgrade(argparse.Namespace(), paths)
        self.assertEqual(result.exit_code, 0)
        self.assertIn("0 of 0 objects upgraded", out.getvalue())
        self.assertIn("Nothing to upgrade", out.getvalue())

    def test_pre_envelope_object_is_upgraded_in_place(self):
        paths = _paths()
        path = _write(
            paths, "knowledge-units/0001.md",
            "---\nhydra_id: hydra://knowledge-unit/0001-fixture\n---\n# Fixture\n",
        )
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            result = schema.command_schema_upgrade(argparse.Namespace(), paths)
        self.assertEqual(result.exit_code, 0)
        self.assertIn("1 of 1 objects upgraded", out.getvalue())
        self.assertIn("hydra://knowledge-unit/0001-fixture", out.getvalue())
        text = path.read_text(encoding="utf-8")
        self.assertIn("uid:", text)
        self.assertIn("schema_version:", text)

    def test_already_current_is_idempotent(self):
        paths = _paths()
        _write(
            paths, "knowledge-units/0001.md",
            "---\nhydra_id: hydra://knowledge-unit/0001-fixture\n---\n# Fixture\n",
        )
        with contextlib.redirect_stdout(io.StringIO()):
            schema.command_schema_upgrade(argparse.Namespace(), paths)
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            result = schema.command_schema_upgrade(argparse.Namespace(), paths)
        self.assertEqual(result.exit_code, 0)
        self.assertIn("0 of 1 objects upgraded", out.getvalue())

    def test_names_the_fields_it_may_not_write_for_you(self):
        # Moved from `test_hydra.py`'s `SchemaUpgradeCommandTests`: the
        # upgrade fills the two slots an empty
        # value is true for and says what it left, rather than letting the
        # next `validate` run be the first anyone hears of it.
        paths = _paths()
        _write(
            paths, "knowledge-units/0001.md",
            "---\nhydra_id: hydra://knowledge-unit/0001-fixture\nkind: knowledge-unit\ntitle: Test Object\n"
            "status: active\nscope: base-seed\n---\n# Test Object\n",
        )
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            result = schema.command_schema_upgrade(argparse.Namespace(), paths)
        output = out.getvalue()
        self.assertEqual(result.exit_code, 0)
        self.assertIn("1 of 1 objects upgraded", output)
        self.assertIn("now need envelope fields no migration may write", output)
        self.assertIn("knowledge-units/0001.md: owners", output)
        # relations and provenance.sources were written, so they are not owed.
        self.assertNotIn("relations", output)
        self.assertNotIn("provenance.sources", output)

    def test_owes_nothing_when_the_envelope_is_complete(self):
        paths = _paths()
        _write(
            paths, "knowledge-units/0001.md",
            "---\nhydra_id: hydra://knowledge-unit/0001-fixture\nkind: knowledge-unit\ntitle: Test Object\n"
            "status: active\nscope: base-seed\nowners:\n  team: hydra\n---\n# Test Object\n",
        )
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            result = schema.command_schema_upgrade(argparse.Namespace(), paths)
        output = out.getvalue()
        self.assertEqual(result.exit_code, 0)
        self.assertIn("1 of 1 objects upgraded", output)
        self.assertNotIn("no migration may write", output)
        self.assertEqual(references.validate_object_references(paths), [])


if __name__ == "__main__":
    unittest.main()
