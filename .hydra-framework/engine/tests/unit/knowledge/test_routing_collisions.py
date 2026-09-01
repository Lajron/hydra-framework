"""Mirror test for `hydra_engine.knowledge.routing_collisions`: the
multi-package merge gate."""

from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

_SRC = Path(__file__).resolve().parents[3] / "src"
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

from hydra_engine.knowledge import packages, routing, routing_collisions  # noqa: E402
from hydra_engine.objects.discovery import ObjectLocations  # noqa: E402


def _context_paths(root: Path) -> packages.ContextCompilerPaths:
    return packages.ContextCompilerPaths(root=root, hydra=root / ".hydra-framework")


def _resolver_paths(root: Path) -> ObjectLocations:
    hydra = root / ".hydra-framework"
    return ObjectLocations(
        root=root, hydra=hydra, local=root / ".hydra-framework.local",
        personal_tasks_rel="tasks/personal", object_registry=hydra / "cognition/graph/registry.yaml",
    )


def _make_package(root: Path, name: str, *, keywords: str = "alpha") -> None:
    pkg = root / ".hydra-framework/repo/knowledge/knowledge-packages" / name
    pkg.mkdir(parents=True)
    (pkg / "overview.md").write_text("# Overview\n", encoding="utf-8")
    (pkg / "routing.yaml").write_text(
        f"schema: {routing.ROUTING_SCHEMA}\npackage: {name}\ntitle: {name.title()}\nkeywords: {keywords}\n",
        encoding="utf-8",
    )


class ValidatePackageRoutingCollisionsTests(unittest.TestCase):
    def test_no_packages_is_clean(self):
        root = Path(tempfile.mkdtemp(prefix="routing-collisions-test-"))
        findings = routing_collisions.validate_package_routing_collisions(_context_paths(root), _resolver_paths(root))
        self.assertEqual(findings, [])

    def test_no_overlap_between_packages_is_clean(self):
        root = Path(tempfile.mkdtemp(prefix="routing-collisions-test-"))
        _make_package(root, "one", keywords="alpha")
        _make_package(root, "two", keywords="beta")
        findings = routing_collisions.validate_package_routing_collisions(_context_paths(root), _resolver_paths(root))
        self.assertEqual(findings, [])

    def test_shared_keyword_is_a_finding_naming_both_owning_teams(self):
        root = Path(tempfile.mkdtemp(prefix="routing-collisions-test-"))
        for name, team in [("first", "team-a"), ("second", "team-b")]:
            pkg = root / ".hydra-framework/repo/knowledge/knowledge-packages" / name
            pkg.mkdir(parents=True)
            (pkg / "overview.md").write_text("# Overview\n", encoding="utf-8")
            (pkg / "routing.yaml").write_text(
                f"schema: {routing.ROUTING_SCHEMA}\npackage: {name}\ntitle: {name.title()}\n"
                f"owners:\n  team: {team}\nkeywords:\n  - shared-topic\n",
                encoding="utf-8",
            )
        findings = routing_collisions.validate_package_routing_collisions(_context_paths(root), _resolver_paths(root))
        self.assertEqual(len(findings), 1)
        detail = findings[0].detail
        self.assertIn("keyword `shared-topic`", detail)
        self.assertIn("first (owned by team-a)", detail)
        self.assertIn("second (owned by team-b)", detail)

    def test_shared_route_name_is_a_finding(self):
        root = Path(tempfile.mkdtemp(prefix="routing-collisions-test-"))
        for name, keyword in [("first", "alpha"), ("second", "beta")]:
            pkg = root / ".hydra-framework/repo/knowledge/knowledge-packages" / name
            pkg.mkdir(parents=True)
            (pkg / "overview.md").write_text("# Overview\n", encoding="utf-8")
            (pkg / "routing.yaml").write_text(
                f"schema: {routing.ROUTING_SCHEMA}\npackage: {name}\ntitle: {name.title()}\n"
                f"keywords:\n  - {keyword}\n"
                "routes:\n  shared_route:\n    use_when:\n      - a task shape\n",
                encoding="utf-8",
            )
        findings = routing_collisions.validate_package_routing_collisions(_context_paths(root), _resolver_paths(root))
        self.assertEqual(len(findings), 1)
        self.assertIn("route `shared_route`", findings[0].detail)

    def test_missing_owners_team_reports_unspecified_rather_than_crashing(self):
        root = Path(tempfile.mkdtemp(prefix="routing-collisions-test-"))
        _make_package(root, "first", keywords="shared-topic")
        _make_package(root, "second", keywords="shared-topic")
        findings = routing_collisions.validate_package_routing_collisions(_context_paths(root), _resolver_paths(root))
        self.assertEqual(len(findings), 1)
        self.assertIn("owned by unspecified", findings[0].detail)


if __name__ == "__main__":
    unittest.main()
