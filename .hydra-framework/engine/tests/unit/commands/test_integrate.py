"""Mirror test for `hydra_engine.commands.integrate`."""

from __future__ import annotations

import argparse
import contextlib
import io as stdlib_io
import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from hydra_engine.cli.dispatch import RepoContext
from hydra_engine.commands import integrate


def _ctx() -> RepoContext:
    root = Path(tempfile.mkdtemp(prefix="commands-integrate-"))
    return RepoContext.for_root(root)


def _write(root: Path, rel: str, content: str) -> Path:
    path = root / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    return path


def _object(hydra_id: str, title: str) -> str:
    return (
        "---\n"
        f"hydra_id: {hydra_id}\n"
        "uid: 33333333-3333-4333-8333-333333333333\n"
        "schema_version: 3\n"
        "kind: knowledge-unit\n"
        f"title: {title}\n"
        "status: active\n"
        "scope: repo-local\n"
        "owners:\n"
        "  team: hydra\n"
        "relations: []\n"
        "provenance:\n"
        "  sources: []\n"
        "---\n\n"
        f"# {title}\n"
    )


class IntegrateCommandTests(unittest.TestCase):
    def test_scan_emits_json(self) -> None:
        ctx = _ctx()
        _write(ctx.root, ".migrations/source-a/.hydra-framework/manifest.yaml", "seed_version: 0.1.0\n")
        _write(ctx.root, ".migrations/source-a/.hydra-framework/repo/knowledge-units/0001.md", _object("hydra://knowledge-unit/0001", "One"))
        args = argparse.Namespace(slug="source-a", json=True)
        out = stdlib_io.StringIO()

        with contextlib.redirect_stdout(out):
            result = integrate.command_integrate_scan(args, ctx)

        self.assertEqual(result.exit_code, 0)
        payload = json.loads(out.getvalue())
        self.assertEqual(payload["slug"], "source-a")
        self.assertEqual(payload["objects"]["total"], 1)

    def test_map_create_reports_created_workspace(self) -> None:
        ctx = _ctx()
        _write(ctx.root, ".migrations/source-a/.hydra-framework/manifest.yaml", "seed_version: 0.1.0\n")
        _write(ctx.root, ".migrations/source-a/.hydra-framework/repo/knowledge-units/0001.md", _object("hydra://knowledge-unit/0001", "One"))
        args = argparse.Namespace(slug="source-a", create=True)
        out = stdlib_io.StringIO()

        with mock.patch("hydra_engine.ports.clock.today", return_value="2026-01-01"):
            with contextlib.redirect_stdout(out):
                result = integrate.command_integrate_map(args, ctx)

        self.assertEqual(result.exit_code, 0)
        self.assertIn("Created workspace: .hydra-framework/intake/integrations/2026-01-01-source-a", out.getvalue())

    def test_identify_requires_existing_workspace(self) -> None:
        ctx = _ctx()
        args = argparse.Namespace(slug="source-a")
        err = stdlib_io.StringIO()

        with contextlib.redirect_stderr(err):
            result = integrate.command_integrate_identify(args, ctx)

        self.assertEqual(result.exit_code, 1)
        self.assertIn("run `hydra.py integrate map source-a --create` first", err.getvalue())

    def test_identify_rewrites_object_map_in_existing_workspace(self) -> None:
        ctx = _ctx()
        _write(ctx.root, ".migrations/source-a/.hydra-framework/manifest.yaml", "seed_version: 0.1.0\n")
        _write(ctx.root, ".migrations/source-a/.hydra-framework/repo/knowledge-units/0001.md", _object("hydra://knowledge-unit/0001", "One"))
        stale = _write(
            ctx.root,
            ".hydra-framework/intake/integrations/2026-01-01-source-a/object-map.yaml",
            "schema: hydra-framework.source-object-map.v1\nslug: source-a\nobjects: []\n",
        )
        args = argparse.Namespace(slug="source-a")
        out = stdlib_io.StringIO()

        with mock.patch("hydra_engine.ports.clock.today", return_value="2026-01-01"):
            with contextlib.redirect_stdout(out):
                result = integrate.command_integrate_identify(args, ctx)

        self.assertEqual(result.exit_code, 0)
        self.assertIn("Object map:", out.getvalue())
        self.assertIn("hydra://source/source-a/knowledge-unit/0001", stale.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
