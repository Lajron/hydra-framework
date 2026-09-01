"""Mirror test for `hydra_engine.commands.seed`."""

from __future__ import annotations

import argparse
import contextlib
import io as stdlib_io
import json
import sys
import tempfile
import unittest
from pathlib import Path

_SRC = Path(__file__).resolve().parents[3] / "src"
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

from hydra_engine.commands import seed  # noqa: E402
from hydra_engine.objects.discovery import ObjectLocations  # noqa: E402
from hydra_engine.seed.paths import SeedPaths  # noqa: E402


def _write(root: Path, rel: str, content: str = "") -> Path:
    path = root / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    return path


def _seed_and_base() -> tuple[SeedPaths, ObjectLocations, Path]:
    root = Path(tempfile.mkdtemp(prefix="commands-seed-"))
    hydra = root / ".hydra-framework"
    hydra.mkdir(parents=True)
    paths = SeedPaths(root=root, hydra=hydra, adaptation_ledger=hydra / "evolution/adaptations.md")
    resolver_paths = ObjectLocations(
        root=root,
        hydra=hydra,
        local=root / ".hydra-framework.local",
        personal_tasks_rel="tasks/personal",
        object_registry=hydra / "cognition/graph/registry.yaml",
    )
    base_root = Path(tempfile.mkdtemp(prefix="commands-seed-base-"))
    (base_root / ".hydra-framework").mkdir(parents=True)
    return paths, resolver_paths, base_root


def _diff_base_args(**overrides: object) -> argparse.Namespace:
    defaults = {"base": "", "json": False, "fail_on_drift": False}
    defaults.update(overrides)
    return argparse.Namespace(**defaults)


class CommandDiffBaseTests(unittest.TestCase):
    def test_missing_base_refuses_on_stderr(self):
        paths, resolver_paths, _base_root = _seed_and_base()
        args = _diff_base_args(base=str(paths.root / "nowhere"))
        err = stdlib_io.StringIO()
        with contextlib.redirect_stderr(err):
            result = seed.command_diff_base(args, paths, resolver_paths, manifest={})
        self.assertEqual(result.exit_code, 1)
        self.assertIn("no framework at", err.getvalue())

    def test_base_same_as_local_refuses(self):
        paths, resolver_paths, _base_root = _seed_and_base()
        args = _diff_base_args(base=str(paths.root))
        err = stdlib_io.StringIO()
        with contextlib.redirect_stderr(err):
            result = seed.command_diff_base(args, paths, resolver_paths, manifest={})
        self.assertEqual(result.exit_code, 1)
        self.assertIn("same directory", err.getvalue())

    def test_identical_trees_report_no_unexplained_differences(self):
        paths, resolver_paths, base_root = _seed_and_base()
        _write(paths.hydra, "manifest.yaml", "seed_version: 0.1.0\n")
        _write(base_root / ".hydra-framework", "manifest.yaml", "seed_version: 0.1.0\n")
        args = _diff_base_args(base=str(base_root), json=True)
        out = stdlib_io.StringIO()
        with contextlib.redirect_stdout(out):
            result = seed.command_diff_base(args, paths, resolver_paths, manifest={"seed_version": "0.1.0"})
        self.assertEqual(result.exit_code, 0)
        payload = json.loads(out.getvalue())
        self.assertEqual(payload["counts"]["unexplained"], 0)

    def test_unexplained_difference_with_fail_on_drift_exits_2(self):
        paths, resolver_paths, base_root = _seed_and_base()
        _write(paths.hydra, "manifest.yaml", "seed_version: 0.1.0\n")
        _write(paths.hydra, "repo/knowledge/example.md", "# Example\n")
        _write(base_root / ".hydra-framework", "manifest.yaml", "seed_version: 0.1.0\n")
        args = _diff_base_args(base=str(base_root), json=True, fail_on_drift=True)
        out = stdlib_io.StringIO()
        with contextlib.redirect_stdout(out):
            result = seed.command_diff_base(args, paths, resolver_paths, manifest={"seed_version": "0.1.0"})
        self.assertEqual(result.exit_code, 2)
        payload = json.loads(out.getvalue())
        self.assertEqual(payload["counts"]["unexplained"], 1)

    def test_text_output_reports_lineage_absence(self):
        paths, resolver_paths, base_root = _seed_and_base()
        _write(paths.hydra, "manifest.yaml", "seed_version: 0.1.0\n")
        _write(base_root / ".hydra-framework", "manifest.yaml", "seed_version: 0.1.0\n")
        args = _diff_base_args(base=str(base_root))
        out = stdlib_io.StringIO()
        with contextlib.redirect_stdout(out):
            result = seed.command_diff_base(args, paths, resolver_paths, manifest={"seed_version": "0.1.0"})
        self.assertEqual(result.exit_code, 0)
        self.assertIn("Lineage: not recorded", out.getvalue())
        self.assertIn("identical:", out.getvalue())


class CommandEvolutionRecordTests(unittest.TestCase):
    @staticmethod
    def _args(**overrides: object) -> argparse.Namespace:
        defaults = {
            "title": "example-change",
            "date": "2026-07-30",
            "base_seed_version": "0.1.0",
            "disposition": "repo-local",
            "path": [".hydra-framework/repo/knowledge/example.md"],
            "why": ["Needed by this repository."],
            "evidence": ["Checked by selftest."],
        }
        defaults.update(overrides)
        return argparse.Namespace(**defaults)

    def test_appended_entry_is_recorded(self):
        paths, _resolver_paths, _base_root = _seed_and_base()
        out = stdlib_io.StringIO()
        with contextlib.redirect_stdout(out):
            result = seed.command_evolution_record(self._args(), paths, manifest={})
        self.assertEqual(result.exit_code, 0)
        self.assertIn("Recorded adaptation:", out.getvalue())
        text = paths.adaptation_ledger.read_text(encoding="utf-8")
        self.assertIn("2026-07-30 - example-change", text)
        self.assertIn("- repo/knowledge/example.md", text)

    def test_invalid_date_is_rejected_without_writing(self):
        paths, _resolver_paths, _base_root = _seed_and_base()
        err = stdlib_io.StringIO()
        with contextlib.redirect_stderr(err):
            result = seed.command_evolution_record(self._args(date="2026-13-01"), paths, manifest={})
        self.assertEqual(result.exit_code, 1)
        self.assertIn("invalid date", err.getvalue())
        self.assertFalse(paths.adaptation_ledger.exists())

    def test_default_base_seed_version_comes_from_manifest(self):
        paths, _resolver_paths, _base_root = _seed_and_base()
        manifest = {"seed_version": "0.4.0"}
        out = stdlib_io.StringIO()
        with contextlib.redirect_stdout(out):
            result = seed.command_evolution_record(self._args(base_seed_version=None), paths, manifest)
        self.assertEqual(result.exit_code, 0)
        self.assertIn("Base seed version: 0.4.0", paths.adaptation_ledger.read_text(encoding="utf-8"))

    def test_appending_never_rewrites_earlier_entries(self):
        paths, _resolver_paths, _base_root = _seed_and_base()
        with contextlib.redirect_stdout(stdlib_io.StringIO()):
            seed.command_evolution_record(self._args(), paths, manifest={})
        first = paths.adaptation_ledger.read_text(encoding="utf-8")
        with contextlib.redirect_stdout(stdlib_io.StringIO()):
            seed.command_evolution_record(self._args(title="second-change"), paths, manifest={})
        second = paths.adaptation_ledger.read_text(encoding="utf-8")
        self.assertTrue(second.startswith(first.rstrip()))


if __name__ == "__main__":
    unittest.main()
