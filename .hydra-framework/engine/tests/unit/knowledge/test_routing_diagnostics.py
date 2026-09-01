"""Mirror test for `hydra_engine.knowledge.routing_diagnostics` (Hydra routing
authority task, Governance and observability)."""

from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

_SRC = Path(__file__).resolve().parents[3] / "src"
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

from hydra_engine.knowledge import packages, routing, routing_diagnostics  # noqa: E402
from hydra_engine.objects.discovery import ObjectLocations  # noqa: E402


def _context_paths(root: Path) -> packages.ContextCompilerPaths:
    return packages.ContextCompilerPaths(root=root, hydra=root / ".hydra-framework")


def _resolver_paths(root: Path) -> ObjectLocations:
    hydra = root / ".hydra-framework"
    return ObjectLocations(
        root=root, hydra=hydra, local=root / ".hydra-framework.local",
        personal_tasks_rel="tasks/personal", object_registry=hydra / "cognition/graph/registry.yaml",
    )


def _make_package(root: Path, name: str, *, keywords: str) -> None:
    pkg = root / ".hydra-framework/repo/knowledge/knowledge-packages" / name
    pkg.mkdir(parents=True)
    (pkg / "overview.md").write_text("# Overview\n", encoding="utf-8")
    (pkg / "routing.yaml").write_text(
        f"schema: {routing.ROUTING_SCHEMA}\npackage: {name}\ntitle: {name.title()}\nkeywords: {keywords}\n",
        encoding="utf-8",
    )


class RoutePromptMatchDiagnosticsTests(unittest.TestCase):
    def test_scores_matching_packages_by_keyword_overlap(self):
        root = Path(tempfile.mkdtemp(prefix="routing-diagnostics-test-"))
        _make_package(root, "solid", keywords="\n  - engine\n  - refactor")
        entries = routing_diagnostics.route_prompt_match_diagnostics(
            "Please do an engine refactor", _context_paths(root), _resolver_paths(root)
        )
        self.assertEqual(len(entries), 1)
        self.assertEqual(entries[0]["package"], "solid")
        self.assertEqual(entries[0]["title"], "Solid")
        self.assertEqual(entries[0]["score"], 1.0)

    def test_non_matching_package_is_excluded_when_not_requested(self):
        root = Path(tempfile.mkdtemp(prefix="routing-diagnostics-test-"))
        _make_package(root, "unrelated", keywords="\n  - unrelated-topic")
        entries = routing_diagnostics.route_prompt_match_diagnostics(
            "Please do an engine refactor", _context_paths(root), _resolver_paths(root)
        )
        self.assertEqual(entries, [])

    def test_explicit_package_slug_is_returned_even_with_a_zero_score(self):
        root = Path(tempfile.mkdtemp(prefix="routing-diagnostics-test-"))
        _make_package(root, "requested", keywords="\n  - unrelated-topic")
        entries = routing_diagnostics.route_prompt_match_diagnostics(
            "Please do an engine refactor", _context_paths(root), _resolver_paths(root), ("requested",),
        )
        self.assertEqual(len(entries), 1)
        self.assertEqual(entries[0]["package"], "requested")
        self.assertEqual(entries[0]["score"], 0.0)

    def test_broken_routing_file_is_skipped_rather_than_raising(self):
        root = Path(tempfile.mkdtemp(prefix="routing-diagnostics-test-"))
        pkg = root / ".hydra-framework/repo/knowledge/knowledge-packages/wrong"
        pkg.mkdir(parents=True)
        (pkg / "routing.yaml").write_text(
            "schema: wrong.schema.v1\npackage: wrong\ntitle: Wrong\nkeywords:\n  - engine\n",
            encoding="utf-8",
        )
        entries = routing_diagnostics.route_prompt_match_diagnostics(
            "Please do an engine refactor", _context_paths(root), _resolver_paths(root)
        )
        self.assertEqual(entries, [])


if __name__ == "__main__":
    unittest.main()
