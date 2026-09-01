"""Mirror test for `hydra_engine.commands.explain_path`."""

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

from hydra_engine.cli.dispatch import RepoContext  # noqa: E402
from hydra_engine.commands import explain_path  # noqa: E402
from hydra_engine.identity.schema_versions import CURRENT_SCHEMA_VERSION  # noqa: E402
from hydra_engine.objects import registry, store_build  # noqa: E402
from hydra_engine.documents.tokens import write_text  # noqa: E402
from hydra_engine.objects import discovery  # noqa: E402

UID = "11111111-1111-4111-8111-111111111111"


def _root() -> Path:
    return Path(tempfile.mkdtemp(prefix="commands-explain-path-"))


def _write(root: Path, rel: str, content: str = "") -> Path:
    path = root / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    return path


def _object_markdown(hydra_id: str, *, relates_to: str = "", provenance_source: str = "", kind: str = "knowledge-unit") -> str:
    relations = f"  - {relates_to}\n" if relates_to else ""
    sources = f"\n    - {provenance_source}" if provenance_source else " []"
    return (
        "---\n"
        f"hydra_id: {hydra_id}\n"
        f"uid: {UID}\n"
        f"schema_version: {CURRENT_SCHEMA_VERSION}\n"
        f"kind: {kind}\n"
        "title: Test Object\n"
        "status: active\n"
        "scope: base-seed\n"
        "owners:\n"
        "  team: hydra\n"
        "relations:\n" + relations +
        "provenance:\n"
        f"  sources:{sources}\n"
        "---\n# Test Object\n"
    )


def _run(args, ctx) -> tuple[int, str]:
    out = stdlib_io.StringIO()
    with contextlib.redirect_stdout(out):
        result = explain_path.command_explain_path(args, ctx)
    return result.exit_code, out.getvalue()


class ExplainPathScanTests(unittest.TestCase):
    def test_finds_the_object_at_the_path_with_reverse_and_forward_relations(self):
        root = _root()
        _write(root, ".hydra-framework/repo/knowledge-units/0001-a.md", _object_markdown("hydra://knowledge-unit/0001-a", relates_to="hydra://knowledge-unit/0002-b"))
        _write(root, ".hydra-framework/repo/knowledge-units/0002-b.md", _object_markdown("hydra://knowledge-unit/0002-b"))

        report = explain_path.explain_path(".hydra-framework/repo/knowledge-units/0002-b.md", RepoContext.for_root(root))

        self.assertEqual(report["source"], "scan")
        self.assertEqual(report["tier"], "shared")
        self.assertEqual(report["object"]["id"], "hydra://knowledge-unit/0002-b")
        self.assertEqual(report["reverse_citations"], ["hydra://knowledge-unit/0001-a"])
        self.assertEqual(report["directory_owner"], "Canonical repository-specific facts, conventions, and procedures.")

    def test_reports_provenance_citers_for_a_non_object_path(self):
        root = _root()
        _write(root, ".hydra-framework/repo/knowledge-units/0001-a.md", _object_markdown("hydra://knowledge-unit/0001-a", provenance_source=".hydra-framework/core/placement-rules.md"))
        _write(root, ".hydra-framework/core/placement-rules.md", "# Placement Rules\n")

        report = explain_path.explain_path(".hydra-framework/core/placement-rules.md", RepoContext.for_root(root))

        self.assertIsNone(report["object"])
        self.assertEqual(report["provenance_citers"], ["hydra://knowledge-unit/0001-a"])
        self.assertEqual(report["directory_owner"], "Stable framework rules, principles, lifecycle, and placement policy.")

    def test_reports_generated_provider_surface(self):
        root = _root()
        _write(root, ".hydra-framework/capabilities/skills/deploy/skill.md", "schema: hydra-framework.skill.v2\nname: deploy\n")
        _write(root, ".claude/skills/deploy/SKILL.md", "---\nname: deploy\n---\nBody.\n")
        _write(root, ".hydra-framework/capabilities/skills/deploy/.hydra-adapter.yaml", "canonical_source: .hydra-framework/capabilities/skills/deploy/skill.md\n")
        target_sidecar = root / ".claude/skills/deploy/.hydra-adapter.yaml"
        target_sidecar.write_text("canonical_source: .hydra-framework/capabilities/skills/deploy/skill.md\n", encoding="utf-8")

        report = explain_path.explain_path(".claude/skills/deploy/SKILL.md", RepoContext.for_root(root))

        self.assertIsNotNone(report["provider_surface"])
        self.assertIn(report["provider_surface"]["status"], {"generated", "drifted", "orphaned", "stale"})
        self.assertEqual(report["provider_surface"]["kind"], "skill")

    def test_reports_authored_provider_declaration(self):
        root = _root()
        _write(root, ".claude/settings.json", "{}\n")

        report = explain_path.explain_path(".claude/settings.json", RepoContext.for_root(root))

        self.assertEqual(report["provider_surface"], {
            "status": "authored",
            "kind": "",
            "detail": "Hand-maintained Claude Code settings.",
        })

    def test_missing_path_still_reports_mechanically(self):
        root = _root()
        report = explain_path.explain_path("nowhere/at/all.md", RepoContext.for_root(root))
        self.assertFalse(report["exists"])
        self.assertIsNone(report["object"])
        self.assertIsNone(report["provider_surface"])

    def test_command_wrapper_emits_json(self):
        root = _root()
        _write(root, ".hydra-framework/repo/knowledge-units/0001-a.md", _object_markdown("hydra://knowledge-unit/0001-a"))
        args = argparse.Namespace(path=".hydra-framework/repo/knowledge-units/0001-a.md", json=True)

        exit_code, text = _run(args, RepoContext.for_root(root))

        self.assertEqual(exit_code, 0)
        payload = json.loads(text)
        self.assertEqual(payload["object"]["id"], "hydra://knowledge-unit/0001-a")

    def test_command_wrapper_human_readable(self):
        root = _root()
        _write(root, ".hydra-framework/repo/knowledge-units/0001-a.md", _object_markdown("hydra://knowledge-unit/0001-a"))
        args = argparse.Namespace(path=".hydra-framework/repo/knowledge-units/0001-a.md", json=False)

        exit_code, text = _run(args, RepoContext.for_root(root))

        self.assertEqual(exit_code, 0)
        self.assertIn("Hydra explain-path", text)
        self.assertIn("hydra://knowledge-unit/0001-a", text)


class ExplainPathStoreTests(unittest.TestCase):
    def test_uses_the_store_when_fresh_and_agrees_with_the_scan_path(self):
        root = _root()
        _write(root, ".hydra-framework/repo/knowledge-units/0001-a.md", _object_markdown("hydra://knowledge-unit/0001-a", relates_to="hydra://knowledge-unit/0002-b"))
        _write(root, ".hydra-framework/repo/knowledge-units/0002-b.md", _object_markdown("hydra://knowledge-unit/0002-b"))
        ctx = RepoContext.for_root(root)
        resolver_paths = ctx.resolver_paths()
        objects, errors = discovery.collect_hydra_objects(resolver_paths)
        assert not errors, errors
        write_text(resolver_paths.object_registry, registry.object_registry_text(objects))
        store_build.rebuild_store(resolver_paths, resolver_paths.local)

        report = explain_path.explain_path(".hydra-framework/repo/knowledge-units/0002-b.md", ctx)

        self.assertEqual(report["source"], "sqlite")
        self.assertEqual(report["object"]["id"], "hydra://knowledge-unit/0002-b")
        self.assertEqual(report["reverse_citations"], ["hydra://knowledge-unit/0001-a"])


if __name__ == "__main__":
    unittest.main()
