"""Mirror test for `hydra_engine.commands.providers`."""

from __future__ import annotations

import argparse
import contextlib
import io as stdlib_io
import sys
import tempfile
import unittest
from pathlib import Path

_SRC = Path(__file__).resolve().parents[3] / "src"
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

from hydra_engine.commands import providers  # noqa: E402
from hydra_engine.providers.paths import ProvidersPaths  # noqa: E402


def _write(root: Path, rel: str, content: str) -> None:
    target = root / rel
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(content, encoding="utf-8")


def _paths_with_one_skill() -> ProvidersPaths:
    root = Path(tempfile.mkdtemp(prefix="commands-providers-"))
    _write(
        root,
        ".hydra-framework/capabilities/skills/demo-skill/metadata.yaml",
        "name: demo-skill\ndescription: Use when relevant.\nkind: procedure\n",
    )
    _write(root, ".hydra-framework/capabilities/skills/demo-skill/skill.md", "# Demo Skill\n\nBody.\n")
    return ProvidersPaths(root=root, hydra=root / ".hydra-framework")


class CommandExportAdaptersTests(unittest.TestCase):
    def test_dry_run_reports_creates_without_writing(self):
        paths = _paths_with_one_skill()
        args = argparse.Namespace(check=False, dry_run=True)
        out = stdlib_io.StringIO()
        with contextlib.redirect_stdout(out):
            result = providers.command_export_adapters(args, paths)
        self.assertEqual(result.exit_code, 0)
        self.assertIn("would write", out.getvalue())
        self.assertFalse((paths.root / ".claude/skills/hydra-demo-skill/SKILL.md").exists())

    def test_writes_generated_files(self):
        paths = _paths_with_one_skill()
        args = argparse.Namespace(check=False, dry_run=False)
        out = stdlib_io.StringIO()
        with contextlib.redirect_stdout(out):
            result = providers.command_export_adapters(args, paths)
        self.assertEqual(result.exit_code, 0)
        self.assertTrue((paths.root / ".claude/skills/hydra-demo-skill/SKILL.md").exists())

    def test_check_reports_drift_and_fails(self):
        paths = _paths_with_one_skill()
        args = argparse.Namespace(check=True, dry_run=False)
        out = stdlib_io.StringIO()
        with contextlib.redirect_stdout(out):
            result = providers.command_export_adapters(args, paths)
        self.assertEqual(result.exit_code, 1)
        self.assertIn("drift detected", out.getvalue())

    def test_check_passes_once_up_to_date(self):
        paths = _paths_with_one_skill()
        with contextlib.redirect_stdout(stdlib_io.StringIO()):
            providers.command_export_adapters(argparse.Namespace(check=False, dry_run=False), paths)
        out = stdlib_io.StringIO()
        with contextlib.redirect_stdout(out):
            result = providers.command_export_adapters(argparse.Namespace(check=True, dry_run=False), paths)
        self.assertEqual(result.exit_code, 0)
        self.assertIn("up to date", out.getvalue())


class CommandReclaimTests(unittest.TestCase):
    def test_no_findings_reports_all_generated(self):
        root = Path(tempfile.mkdtemp(prefix="commands-reclaim-"))
        paths = ProvidersPaths(root=root, hydra=root / ".hydra-framework")
        args = argparse.Namespace(json=False, promote=False, fail_on_findings=False)
        out = stdlib_io.StringIO()
        with contextlib.redirect_stdout(out):
            result = providers.command_reclaim(args, paths)
        self.assertEqual(result.exit_code, 0)
        self.assertIn("All provider files are generated", out.getvalue())

    def test_orphaned_reports_findings_and_respects_fail_on_findings(self):
        root = Path(tempfile.mkdtemp(prefix="commands-reclaim-orphaned-"))
        _write(root, ".claude/skills/deploy/SKILL.md", "content\n")
        paths = ProvidersPaths(root=root, hydra=root / ".hydra-framework")
        args = argparse.Namespace(json=False, promote=False, fail_on_findings=True)
        out = stdlib_io.StringIO()
        with contextlib.redirect_stdout(out):
            result = providers.command_reclaim(args, paths)
        self.assertEqual(result.exit_code, 1)
        self.assertIn("orphaned: 1", out.getvalue())

    def test_promote_moves_orphaned_files_into_canonical_hydra(self):
        root = Path(tempfile.mkdtemp(prefix="commands-reclaim-promote-"))
        _write(root, ".claude/skills/deploy/SKILL.md", "---\nname: deploy\n---\nBody.\n")
        paths = ProvidersPaths(root=root, hydra=root / ".hydra-framework")
        args = argparse.Namespace(json=False, promote=True, fail_on_findings=False)
        out = stdlib_io.StringIO()
        with contextlib.redirect_stdout(out):
            result = providers.command_reclaim(args, paths)
        self.assertEqual(result.exit_code, 0)
        self.assertTrue((paths.hydra / "capabilities/skills/deploy/skill.md").exists())
        self.assertIn("promoted:", out.getvalue())

    def test_json_flag_short_circuits_to_a_json_report(self):
        root = Path(tempfile.mkdtemp(prefix="commands-reclaim-json-"))
        paths = ProvidersPaths(root=root, hydra=root / ".hydra-framework")
        args = argparse.Namespace(json=True, promote=False, fail_on_findings=False)
        out = stdlib_io.StringIO()
        with contextlib.redirect_stdout(out):
            result = providers.command_reclaim(args, paths)
        self.assertEqual(result.exit_code, 0)
        self.assertEqual(out.getvalue().strip(), "[]")


if __name__ == "__main__":
    unittest.main()
