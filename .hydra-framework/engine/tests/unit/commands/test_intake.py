"""Mirror test for `hydra_engine.commands.intake`."""

from __future__ import annotations

import argparse
import contextlib
import io as stdlib_io
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

_SRC = Path(__file__).resolve().parents[3] / "src"
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

from hydra_engine.commands import intake  # noqa: E402
from hydra_engine.intake.paths import IntakePaths  # noqa: E402


def _paths() -> IntakePaths:
    root = Path(tempfile.mkdtemp(prefix="commands-intake-"))
    return IntakePaths(root=root, hydra=root / ".hydra-framework")


def _seed(paths: IntakePaths, rel: str, content: str) -> Path:
    path = paths.root / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    return path


class CommandMigrationInventoryTests(unittest.TestCase):
    def test_emits_json(self):
        paths = _paths()
        _seed(paths, ".migrations/legacy-ai/AGENTS.md", "# Old agent rules\n")
        args = argparse.Namespace(slug="", json=True)
        out = stdlib_io.StringIO()
        with mock.patch("hydra_engine.ports.git.tracked_files", return_value=[]):
            with contextlib.redirect_stdout(out):
                result = intake.command_migration_inventory(args, paths)
        self.assertEqual(result.exit_code, 0)
        payload = json.loads(out.getvalue())
        self.assertEqual(payload["totals"]["sources"], 1)
        self.assertEqual(payload["sources"][0]["path"], ".migrations/legacy-ai")

    def test_human_readable_reports_totals(self):
        paths = _paths()
        _seed(paths, ".migrations/legacy-ai/AGENTS.md", "# Old agent rules\n")
        args = argparse.Namespace(slug="", json=False)
        out = stdlib_io.StringIO()
        with mock.patch("hydra_engine.ports.git.tracked_files", return_value=[]):
            with contextlib.redirect_stdout(out):
                result = intake.command_migration_inventory(args, paths)
        self.assertEqual(result.exit_code, 0)
        self.assertIn("Hydra migration inventory", out.getvalue())
        self.assertIn("1 source(s)", out.getvalue())

    def test_invalid_slug_reports_error_on_stderr(self):
        paths = _paths()
        args = argparse.Namespace(slug="../outside", json=False)
        err = stdlib_io.StringIO()
        with contextlib.redirect_stderr(err):
            result = intake.command_migration_inventory(args, paths)
        self.assertEqual(result.exit_code, 1)
        self.assertIn("invalid migration slug", err.getvalue())


class CommandMigrationLedgerTests(unittest.TestCase):
    def test_emits_json(self):
        paths = _paths()
        _seed(paths, ".migrations/legacy-ai/AGENTS.md", "# Old agent rules\n")
        args = argparse.Namespace(slug="legacy-ai", create=False, json=True)
        out = stdlib_io.StringIO()
        with mock.patch("hydra_engine.ports.git.tracked_files", return_value=[]):
            with contextlib.redirect_stdout(out):
                result = intake.command_migration_ledger(args, paths)
        self.assertEqual(result.exit_code, 0)
        payload = json.loads(out.getvalue())
        self.assertEqual(payload["source_path"], ".migrations/legacy-ai")

    def test_create_writes_workspace_and_reports_it(self):
        paths = _paths()
        _seed(paths, ".migrations/legacy-ai/AGENTS.md", "# Old agent rules\n")
        args = argparse.Namespace(slug="legacy-ai", create=True, json=False)
        out = stdlib_io.StringIO()
        with mock.patch("hydra_engine.ports.git.tracked_files", return_value=[]):
            with contextlib.redirect_stdout(out):
                result = intake.command_migration_ledger(args, paths)
        self.assertEqual(result.exit_code, 0)
        self.assertIn("Created workspace:", out.getvalue())

    def test_unknown_slug_reports_error_on_stderr(self):
        paths = _paths()
        args = argparse.Namespace(slug="nope", create=True, json=False)
        err = stdlib_io.StringIO()
        with mock.patch("hydra_engine.ports.git.tracked_files", return_value=[]):
            with contextlib.redirect_stderr(err):
                result = intake.command_migration_ledger(args, paths)
        self.assertEqual(result.exit_code, 1)
        self.assertIn("no staged source found", err.getvalue())


class CommandMigrationBatchTests(unittest.TestCase):
    def test_request_stage_emits_machine_readable_state(self):
        paths = _paths()
        args = argparse.Namespace(
            slug="legacy-ai",
            batch="docs",
            source=["incoming"],
            route="shared",
            worker_instance=["drafter-1"],
            capability_class="tool-heavy",
            json=True,
        )
        expected = {"slug": "legacy-ai", "batch": "docs", "phase": "awaiting-staging-approval"}
        out = stdlib_io.StringIO()
        with (
            mock.patch.object(intake.approval, "request_staging", return_value=expected) as request,
            contextlib.redirect_stdout(out),
        ):
            result = intake.command_migration_request_stage(args, paths)
        self.assertEqual(result.exit_code, 0)
        self.assertEqual(json.loads(out.getvalue()), expected)
        request.assert_called_once_with(
            paths,
            "legacy-ai",
            "docs",
            [{"path": "incoming", "route": "shared"}],
            drafting_chain=["drafter-1"],
            capability_class="tool-heavy",
        )

    def test_propose_reads_a_repository_local_json_manifest(self):
        paths = _paths()
        manifest = _seed(paths, "proposal.json", '{"package_slug":"docs","units":[]}\n')
        args = argparse.Namespace(slug="legacy-ai", batch="docs", manifest=str(manifest), json=True)
        expected = {"slug": "legacy-ai", "batch": "docs", "phase": "awaiting-independent-validation"}
        out = stdlib_io.StringIO()
        with (
            mock.patch.object(intake.approval, "submit_proposal", return_value=expected) as submit,
            contextlib.redirect_stdout(out),
        ):
            result = intake.command_migration_propose(args, paths)
        self.assertEqual(result.exit_code, 0)
        self.assertEqual(json.loads(out.getvalue()), expected)
        submit.assert_called_once_with(paths, "legacy-ai", "docs", {"package_slug": "docs", "units": []})

    def test_reject_error_is_reported_without_traceback(self):
        paths = _paths()
        args = argparse.Namespace(
            slug="legacy-ai", batch="docs", outcome="reject", actor="", rationale="", guidance="", json=False
        )
        err = stdlib_io.StringIO()
        with (
            mock.patch.object(intake.approval, "decide", side_effect=ValueError("reject requires rationale")),
            contextlib.redirect_stderr(err),
        ):
            result = intake.command_migration_decide(args, paths)
        self.assertEqual(result.exit_code, 1)
        self.assertIn("reject requires rationale", err.getvalue())


if __name__ == "__main__":
    unittest.main()
