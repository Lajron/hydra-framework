"""Mirror test for `hydra_engine.commands.takeover`."""

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

from hydra_engine.cli.dispatch import RepoContext  # noqa: E402
from hydra_engine.commands import takeover  # noqa: E402


def _root() -> Path:
    return Path(tempfile.mkdtemp(prefix="commands-takeover-"))


def _write(root: Path, rel: str, content: str = "") -> Path:
    path = root / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    return path


class CommandTakeoverScanTests(unittest.TestCase):
    def test_emits_json(self):
        root = _root()
        _write(root, ".cursorrules", "Rules.\n")
        args = argparse.Namespace(root=None, json=True)
        out = stdlib_io.StringIO()
        with mock.patch("hydra_engine.ports.git.tracked_files", return_value=[]):
            with mock.patch("hydra_engine.ports.git.ignore_match", return_value=""):
                with contextlib.redirect_stdout(out):
                    result = takeover.command_takeover_scan(args, RepoContext.for_root(root))
        self.assertEqual(result.exit_code, 0)
        payload = json.loads(out.getvalue())
        self.assertEqual(payload["candidates"][0]["path"], ".cursorrules")

    def test_human_readable_reports_candidates_and_staging(self):
        root = _root()
        _write(root, ".claude/skills/deploy/SKILL.md", "Body.\n")
        args = argparse.Namespace(root=None, json=False)
        out = stdlib_io.StringIO()
        with mock.patch("hydra_engine.ports.git.tracked_files", return_value=[".claude/skills/deploy/SKILL.md"]):
            with mock.patch("hydra_engine.ports.git.ignore_match", return_value=""):
                with contextlib.redirect_stdout(out):
                    result = takeover.command_takeover_scan(args, RepoContext.for_root(root))
        self.assertEqual(result.exit_code, 0)
        text = out.getvalue()
        self.assertIn("Hydra takeover scan", text)
        self.assertIn(".claude (claude): provider-native", text)
        self.assertIn("staging path: .migrations/claude/", text)

    def test_missing_root_reports_error(self):
        root = _root()
        args = argparse.Namespace(root="missing", json=False)
        err = stdlib_io.StringIO()
        with contextlib.redirect_stderr(err):
            result = takeover.command_takeover_scan(args, RepoContext.for_root(root))
        self.assertEqual(result.exit_code, 1)
        self.assertIn("root is not a directory", err.getvalue())


if __name__ == "__main__":
    unittest.main()
