"""Mirror test for `hydra_engine.intake.integration_workspace`."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from hydra_engine.intake import integration_workspace
from hydra_engine.intake.paths import IntakePaths


def _paths() -> IntakePaths:
    root = Path(tempfile.mkdtemp(prefix="integration-workspace-"))
    return IntakePaths(root=root, hydra=root / ".hydra-framework")


def _write(paths: IntakePaths, rel: str, content: str) -> Path:
    path = paths.root / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    return path


class IntegrationWorkspaceStatusTests(unittest.TestCase):
    def test_status_counts_open_terminal_and_collision_rows(self) -> None:
        paths = _paths()
        _write(paths, ".hydra-framework/intake/integrations/2026-01-01-source-a/README.md", "# Source\n")
        _write(paths, ".hydra-framework/intake/integrations/2026-01-01-source-a/object-map.yaml", (
            "schema: hydra-framework.source-object-map.v1\n"
            "slug: source-a\n"
            "objects:\n"
            "  - source_id: hydra://source/source-a/knowledge-unit/one\n"
            "    status: promoted\n"
            "  - source_id: hydra://source/source-a/knowledge-unit/two\n"
            "    status: pending\n"
        ))
        _write(paths, ".hydra-framework/intake/integrations/2026-01-01-source-a/collisions.yaml", (
            "schema: hydra-framework.source-collisions.v1\n"
            "slug: source-a\n"
            "id_collisions:\n"
            "  - type: collision\n"
            "    source_original_id: hydra://knowledge-unit/one\n"
            "path_collisions:\n"
            "  - none\n"
            "ambiguous_matches:\n"
            "  - none\n"
        ))
        _write(paths, ".hydra-framework/intake/integrations/2026-01-01-source-a/ledger.md", (
            "| Source Object | Source ID | Verdict | Destination | Status | Notes |\n"
            "| --- | --- | --- | --- | --- | --- |\n"
            "| `hydra://knowledge-unit/one` | `hydra://source/source-a/knowledge-unit/one` | link | local | promoted | done |\n"
            "| `hydra://knowledge-unit/two` | `hydra://source/source-a/knowledge-unit/two` | import | TBD | pending | todo |\n"
        ))

        status = integration_workspace.status(paths, "source-a")

        self.assertEqual(status["progress"]["total"], 2)
        self.assertEqual(status["progress"]["terminal"], 1)
        self.assertEqual(status["progress"]["open"], 1)
        self.assertEqual(status["collisions"]["id"], 1)
        self.assertEqual(status["object_map_rows"], 2)


if __name__ == "__main__":
    unittest.main()
