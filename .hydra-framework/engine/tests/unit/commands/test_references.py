"""Mirror test for `hydra_engine.commands.references`."""

from __future__ import annotations

import argparse
import contextlib
import io
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

_SRC = Path(__file__).resolve().parents[3] / "src"
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

from hydra_engine.commands import references  # noqa: E402
from hydra_engine.documents.tokens import write_text  # noqa: E402
from hydra_engine.objects import discovery, registry, store_build  # noqa: E402
from hydra_engine.objects.discovery import ObjectLocations  # noqa: E402


def _paths() -> ObjectLocations:
    root = Path(tempfile.mkdtemp(prefix="commands-references-"))
    hydra = root / ".hydra-framework"
    hydra.mkdir(parents=True)
    return ObjectLocations(
        root=root,
        hydra=hydra,
        local=root / ".hydra-framework.local",
        personal_tasks_rel="tasks/personal",
        object_registry=hydra / "cognition/graph/registry.yaml",
    )


def _object_markdown(hydra_id: str, *, uid: str = "00000000-0000-0000-0000-000000000000", title: str = "Fixture") -> str:
    return (
        "---\n"
        f"hydra_id: {hydra_id}\n"
        f"uid: {uid}\n"
        "schema_version: 3\n"
        "kind: knowledge-unit\n"
        f"title: {title}\n"
        "status: active\n"
        "scope: repo\n"
        "owners:\n"
        "  team: fixture\n"
        "relations: []\n"
        "provenance:\n"
        "  sources: []\n"
        "---\n"
        f"# {title}\n"
    )


def _write(paths: ObjectLocations, rel: str, content: str) -> Path:
    path = paths.hydra / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    return path


def _index(paths: ObjectLocations) -> None:
    objects, errors = discovery.collect_hydra_objects(paths)
    assert not errors, errors
    write_text(paths.object_registry, registry.object_registry_text(objects))


def _build_store(paths: ObjectLocations) -> None:
    _index(paths)
    store_build.rebuild_store(paths, paths.local)


class CommandRefResolveTests(unittest.TestCase):
    def test_resolves_by_id(self):
        paths = _paths()
        _write(paths, "knowledge-units/0001.md", _object_markdown("hydra://knowledge-unit/0001-fixture"))
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            result = references.command_ref_resolve(argparse.Namespace(hydra_id="hydra://knowledge-unit/0001-fixture"), paths)
        self.assertEqual(result.exit_code, 0)
        self.assertIn("id: hydra://knowledge-unit/0001-fixture", out.getvalue())

    def test_not_found_refuses_on_stderr(self):
        paths = _paths()
        err = io.StringIO()
        with contextlib.redirect_stderr(err):
            result = references.command_ref_resolve(argparse.Namespace(hydra_id="hydra://knowledge-unit/missing"), paths)
        self.assertEqual(result.exit_code, 1)
        self.assertIn("Hydra object not found", err.getvalue())

    def test_rejects_ambiguous_alias(self):
        paths = _paths()
        _write(paths, "knowledge-units/0001-a.md", _object_markdown("hydra://knowledge-unit/0001-a"))
        _write(
            paths, "knowledge-units/0002-b.md",
            _object_markdown("hydra://knowledge-unit/0002-b").replace(
                "relations: []", "aliases:\n  - hydra://knowledge-unit/0001-a\nrelations: []",
            ),
        )
        err = io.StringIO()
        with contextlib.redirect_stderr(err):
            result = references.command_ref_resolve(argparse.Namespace(hydra_id="hydra://knowledge-unit/0001-a"), paths)
        self.assertEqual(result.exit_code, 1)
        self.assertIn("ambiguous", err.getvalue())


class CommandRefCheckTests(unittest.TestCase):
    def test_clean_tree_reports_ok(self):
        paths = _paths()
        _write(paths, "knowledge-units/0001.md", _object_markdown("hydra://knowledge-unit/0001-fixture"))
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            result = references.command_ref_check(argparse.Namespace(), paths)
        self.assertEqual(result.exit_code, 0)
        self.assertIn("Hydra references: ok (1 objects)", out.getvalue())

    def test_reports_pending_schema_upgrades(self):
        paths = _paths()
        _write(
            paths, "knowledge-units/0001.md",
            "---\nhydra_id: hydra://knowledge-unit/0001-fixture\nkind: knowledge-unit\ntitle: Fixture\nstatus: active\n"
            "scope: repo\nrelations: []\nprovenance:\n  sources: []\n---\n# Fixture\n",
        )
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            result = references.command_ref_check(argparse.Namespace(), paths)
        self.assertEqual(result.exit_code, 0)
        self.assertEqual(out.getvalue(), "Hydra references: ok (1 objects, 1 pending schema upgrade)\n")

    def test_broken_reference_fails(self):
        paths = _paths()
        _write(
            paths, "knowledge-units/0001.md",
            _object_markdown("hydra://knowledge-unit/0001-fixture").replace(
                "relations: []", "relations:\n- hydra://knowledge-unit/missing"
            ),
        )
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            result = references.command_ref_check(argparse.Namespace(), paths)
        self.assertEqual(result.exit_code, 1)
        self.assertIn("Hydra references: failed", out.getvalue())


class CommandRefIndexTests(unittest.TestCase):
    def test_writes_registry(self):
        paths = _paths()
        _write(paths, "knowledge-units/0001.md", _object_markdown("hydra://knowledge-unit/0001-fixture"))
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            result = references.command_ref_index(argparse.Namespace(), paths)
        self.assertEqual(result.exit_code, 0)
        self.assertIn("Indexed 1 objects", out.getvalue())
        self.assertTrue(paths.object_registry.exists())

    def test_broken_reference_refuses_without_writing(self):
        paths = _paths()
        _write(
            paths, "knowledge-units/0001.md",
            _object_markdown("hydra://knowledge-unit/0001-fixture").replace(
                "relations: []", "relations:\n- hydra://knowledge-unit/missing"
            ),
        )
        err = io.StringIO()
        with contextlib.redirect_stderr(err):
            result = references.command_ref_index(argparse.Namespace(), paths)
        self.assertEqual(result.exit_code, 1)
        self.assertFalse(paths.object_registry.exists())

    def test_registry_write_refusal_from_a_concurrency_race_fails_on_stderr(self):
        # B3: `validate_object_references` can pass and a second, separate
        # `collect_hydra_objects` scan inside `write_object_registry` can
        # still race a concurrent atomic replace -- exercised here by
        # forcing that refusal rather than reproducing the race itself.
        paths = _paths()
        _write(paths, "knowledge-units/0001.md", _object_markdown("hydra://knowledge-unit/0001-fixture"))
        err = io.StringIO()
        with mock.patch.object(references, "write_object_registry", return_value=None):
            with contextlib.redirect_stderr(err):
                result = references.command_ref_index(argparse.Namespace(), paths)
        self.assertEqual(result.exit_code, 1)
        self.assertIn("registry write refused", err.getvalue())
        self.assertFalse(paths.object_registry.exists())


class CommandRefResolveStoreBackedTests(unittest.TestCase):
    """`ref resolve` reads through a
    fresh store and reports `source=`; it degrades to the scan path
    (identical output, `source=scan`) when the store is stale, absent, or
    disabled."""

    def test_resolves_from_a_fresh_store_and_reports_source(self):
        paths = _paths()
        _write(paths, "knowledge-units/0001.md", _object_markdown("hydra://knowledge-unit/0001-fixture"))
        _build_store(paths)
        out, err = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            result = references.command_ref_resolve(argparse.Namespace(hydra_id="hydra://knowledge-unit/0001-fixture"), paths)
        self.assertEqual(result.exit_code, 0)
        self.assertIn("id: hydra://knowledge-unit/0001-fixture", out.getvalue())
        self.assertIn("source=sqlite", err.getvalue())

    def test_not_found_in_a_fresh_store_reports_source_sqlite(self):
        paths = _paths()
        _write(paths, "knowledge-units/0001.md", _object_markdown("hydra://knowledge-unit/0001-fixture"))
        _build_store(paths)
        err = io.StringIO()
        with contextlib.redirect_stderr(err):
            result = references.command_ref_resolve(argparse.Namespace(hydra_id="hydra://knowledge-unit/missing"), paths)
        self.assertEqual(result.exit_code, 1)
        self.assertIn("Hydra object not found", err.getvalue())
        self.assertIn("source=sqlite", err.getvalue())

    def test_stale_store_falls_back_to_scan(self):
        paths = _paths()
        _write(paths, "knowledge-units/0001.md", _object_markdown("hydra://knowledge-unit/0001-fixture"))
        _build_store(paths)
        _write(paths, "knowledge-units/0002.md", _object_markdown("hydra://knowledge-unit/0002-other"))
        _index(paths)  # export changed since the store was built; store is now stale
        out, err = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            result = references.command_ref_resolve(argparse.Namespace(hydra_id="hydra://knowledge-unit/0002-other"), paths)
        self.assertEqual(result.exit_code, 0)
        self.assertIn("id: hydra://knowledge-unit/0002-other", out.getvalue())
        self.assertIn("source=scan", err.getvalue())

    def test_disabled_by_env_var_falls_back_to_scan(self):
        paths = _paths()
        _write(paths, "knowledge-units/0001.md", _object_markdown("hydra://knowledge-unit/0001-fixture"))
        _build_store(paths)
        err = io.StringIO()
        with mock.patch.dict("os.environ", {"HYDRA_QUERY_STORE": "off"}):
            with contextlib.redirect_stderr(err):
                result = references.command_ref_resolve(argparse.Namespace(hydra_id="hydra://knowledge-unit/0001-fixture"), paths)
        self.assertEqual(result.exit_code, 0)
        self.assertIn("source=scan", err.getvalue())


class CommandRefRdepsTests(unittest.TestCase):
    def test_reports_not_available_without_a_store(self):
        paths = _paths()
        err = io.StringIO()
        with contextlib.redirect_stderr(err):
            result = references.command_ref_rdeps(argparse.Namespace(hydra_id="hydra://knowledge-unit/0001-fixture"), paths)
        self.assertEqual(result.exit_code, 1)
        self.assertIn("not available", err.getvalue())

    def test_lists_citers_from_the_store(self):
        paths = _paths()
        _write(paths, "knowledge-units/0001-a.md", _object_markdown("hydra://knowledge-unit/0001-a"))
        _write(
            paths, "knowledge-units/0002-b.md",
            _object_markdown("hydra://knowledge-unit/0002-b").replace("relations: []", "relations:\n  - hydra://knowledge-unit/0001-a"),
        )
        _build_store(paths)
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            result = references.command_ref_rdeps(argparse.Namespace(hydra_id="hydra://knowledge-unit/0001-a"), paths)
        self.assertEqual(result.exit_code, 0)
        self.assertIn("hydra://knowledge-unit/0002-b", out.getvalue())

    def test_unknown_id_fails_even_with_a_store(self):
        paths = _paths()
        _write(paths, "knowledge-units/0001-a.md", _object_markdown("hydra://knowledge-unit/0001-a"))
        _build_store(paths)
        err = io.StringIO()
        with contextlib.redirect_stderr(err):
            result = references.command_ref_rdeps(argparse.Namespace(hydra_id="hydra://knowledge-unit/missing"), paths)
        self.assertEqual(result.exit_code, 1)
        self.assertIn("not found", err.getvalue())


class CommandRefImpactTests(unittest.TestCase):
    def test_reports_not_available_without_a_store(self):
        paths = _paths()
        err = io.StringIO()
        with contextlib.redirect_stderr(err):
            result = references.command_ref_impact(argparse.Namespace(hydra_id="hydra://knowledge-unit/0001-a", depth=None), paths)
        self.assertEqual(result.exit_code, 1)
        self.assertIn("not available", err.getvalue())

    def test_lists_transitive_relations_and_default_depth(self):
        paths = _paths()
        _write(
            paths, "knowledge-units/0001-a.md",
            _object_markdown("hydra://knowledge-unit/0001-a").replace("relations: []", "relations:\n  - hydra://knowledge-unit/0002-b"),
        )
        _write(paths, "knowledge-units/0002-b.md", _object_markdown("hydra://knowledge-unit/0002-b"))
        _build_store(paths)
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            result = references.command_ref_impact(argparse.Namespace(hydra_id="hydra://knowledge-unit/0001-a", depth=None), paths)
        self.assertEqual(result.exit_code, 0)
        self.assertIn("hydra://knowledge-unit/0002-b", out.getvalue())
        self.assertIn("depth: 5", out.getvalue())

    def test_custom_depth_is_reported(self):
        paths = _paths()
        _write(paths, "knowledge-units/0001-a.md", _object_markdown("hydra://knowledge-unit/0001-a"))
        _build_store(paths)
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            result = references.command_ref_impact(argparse.Namespace(hydra_id="hydra://knowledge-unit/0001-a", depth=2), paths)
        self.assertEqual(result.exit_code, 0)
        self.assertIn("depth: 2", out.getvalue())


if __name__ == "__main__":
    unittest.main()
