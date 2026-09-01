"""Mirror test for `hydra_engine.intake.integration`."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest import mock

from hydra_engine.intake import integration
from hydra_engine.intake.paths import IntakePaths
from hydra_engine.objects.discovery import ObjectLocations


def _paths() -> IntakePaths:
    root = Path(tempfile.mkdtemp(prefix="integration-intake-"))
    return IntakePaths(root=root, hydra=root / ".hydra-framework")


def _locations(paths: IntakePaths) -> ObjectLocations:
    return ObjectLocations(
        root=paths.root,
        hydra=paths.hydra,
        local=paths.root / ".hydra-framework.local",
        personal_tasks_rel="tasks/personal",
        object_registry=paths.hydra / "cognition/graph/registry.yaml",
    )


def _write(paths: IntakePaths, rel: str, content: str) -> Path:
    path = paths.root / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    return path


def _object(hydra_id: str, title: str, kind: str = "knowledge-unit", uid: str = "11111111-1111-4111-8111-111111111111") -> str:
    return (
        "---\n"
        f"hydra_id: {hydra_id}\n"
        f"uid: {uid}\n"
        "schema_version: 3\n"
        f"kind: {kind}\n"
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


class IntegrationScanTests(unittest.TestCase):
    def test_scan_reports_staged_hydra_source_without_writes(self) -> None:
        paths = _paths()
        _write(paths, ".migrations/example-source/.hydra-framework/manifest.yaml", (
            "schema: hydra-framework.manifest.v1\n"
            "framework_name: hydra-framework\n"
            "seed_version: 0.1.0\n"
            "lineage:\n"
            "  adopted_into: example-source\n"
        ))
        _write(paths, ".migrations/example-source/.hydra-framework/repo/knowledge-units/0001-test.md", _object("hydra://knowledge-unit/0001-test", "Test Unit"))
        _write(paths, ".migrations/example-source/.env", "TOKEN=secret\n")
        before = sorted(path.relative_to(paths.root).as_posix() for path in paths.root.rglob("*") if path.is_file())

        with mock.patch("hydra_engine.ports.git.tracked_files", return_value=[]):
            report = integration.integration_scan(paths, "example-source", _locations(paths))

        after = sorted(path.relative_to(paths.root).as_posix() for path in paths.root.rglob("*") if path.is_file())
        self.assertEqual(before, after)
        self.assertEqual(report["project_name"], "example-source")
        self.assertEqual(report["seed_version"], "0.1.0")
        self.assertEqual(report["objects"]["total"], 1)
        self.assertEqual(report["private_material_risk"], {"credential-or-private-risk": 1})

    def test_object_map_mints_source_scoped_ids_and_matches_by_uid_first(self) -> None:
        paths = _paths()
        uid = "22222222-2222-4222-8222-222222222222"
        _write(paths, ".migrations/source-a/.hydra-framework/manifest.yaml", "seed_version: 0.1.0\n")
        _write(paths, ".migrations/source-a/.hydra-framework/repo/knowledge-units/0002-source.md", _object("hydra://knowledge-unit/0002-source", "Source Unit", uid=uid))
        _write(paths, ".hydra-framework/repo/knowledge-units/0099-local.md", _object("hydra://knowledge-unit/0099-local", "Different Local", uid=uid))

        with mock.patch("hydra_engine.ports.clock.today", return_value="2026-01-01"):
            mapping = integration.integration_object_map(paths, "source-a", _locations(paths))

        row = mapping["objects"][0]
        self.assertEqual(row["source_id"], "hydra://source/source-a/knowledge-unit/0002-source")
        self.assertEqual(row["match_method"], "uid")
        self.assertEqual(row["local_id"], "hydra://knowledge-unit/0099-local")
        self.assertEqual(row["verdict"], "link")

    def test_create_workspace_writes_exact_four_files_and_leaves_source_tree(self) -> None:
        paths = _paths()
        _write(paths, ".migrations/source-a/.hydra-framework/manifest.yaml", "seed_version: 0.1.0\n")
        source_object = _write(paths, ".migrations/source-a/.hydra-framework/repo/knowledge-units/0002-source.md", _object("hydra://knowledge-unit/0002-source", "Source Unit"))
        before = source_object.read_text(encoding="utf-8")

        with mock.patch("hydra_engine.ports.clock.today", return_value="2026-01-01"):
            report = integration.create_integration_workspace(paths, "source-a", _locations(paths))

        workspace = paths.root / report["created_workspace"]
        self.assertEqual(sorted(path.name for path in workspace.iterdir()), ["README.md", "collisions.yaml", "ledger.md", "object-map.yaml"])
        self.assertEqual(source_object.read_text(encoding="utf-8"), before)


if __name__ == "__main__":
    unittest.main()
