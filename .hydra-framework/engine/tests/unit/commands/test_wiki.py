"""Mirror test for `hydra_engine.commands.wiki`."""

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

from hydra_engine.commands import wiki  # noqa: E402
from hydra_engine.wiki.paths import WikiPaths  # noqa: E402


def _paths() -> WikiPaths:
    root = Path(tempfile.mkdtemp(prefix="commands-wiki-"))
    return WikiPaths(root=root, project_wiki=root / "project-wiki")


class CommandValidateWikiTests(unittest.TestCase):
    def test_no_errors_reports_ok(self):
        paths = _paths()
        paths.project_wiki.mkdir(parents=True)
        args = argparse.Namespace(path=None)
        out = stdlib_io.StringIO()
        with contextlib.redirect_stdout(out):
            result = wiki.command_validate_wiki(args, paths)
        self.assertEqual(result.exit_code, 0)
        self.assertIn("Hydra wiki docs: ok", out.getvalue())

    def test_broken_link_reports_failure(self):
        paths = _paths()
        paths.project_wiki.mkdir(parents=True)
        (paths.project_wiki / "home.md").write_text("[[missing]]\n", encoding="utf-8")
        args = argparse.Namespace(path=None)
        out = stdlib_io.StringIO()
        with contextlib.redirect_stdout(out):
            result = wiki.command_validate_wiki(args, paths)
        self.assertEqual(result.exit_code, 1)
        self.assertIn("Hydra wiki docs: failed", out.getvalue())
        self.assertIn("missing", out.getvalue())


class CommandWikiScaffoldTests(unittest.TestCase):
    def test_creates_home_and_sources_pages(self):
        paths = _paths()
        args = argparse.Namespace(project="demo-project", title="", force=False)
        out = stdlib_io.StringIO()
        with contextlib.redirect_stdout(out):
            result = wiki.command_wiki_scaffold(args, paths)
        self.assertEqual(result.exit_code, 0)
        self.assertTrue((paths.project_wiki / "demo-project" / "home.md").exists())
        self.assertTrue((paths.project_wiki / "demo-project" / "sources.md").exists())
        self.assertIn("Created wiki surface:", out.getvalue())

    def test_refuses_to_overwrite_without_force(self):
        paths = _paths()
        target = paths.project_wiki / "demo-project"
        target.mkdir(parents=True)
        (target / "home.md").write_text("existing\n", encoding="utf-8")
        args = argparse.Namespace(project="demo-project", title="", force=False)
        out = stdlib_io.StringIO()
        with contextlib.redirect_stdout(out):
            result = wiki.command_wiki_scaffold(args, paths)
        self.assertEqual(result.exit_code, 1)
        self.assertIn("already exists", out.getvalue())


if __name__ == "__main__":
    unittest.main()
