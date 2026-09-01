"""Mirror test for `hydra_engine.intake.inventory`."""

from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

_SRC = Path(__file__).resolve().parents[3] / "src"
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

from hydra_engine.intake import inventory  # noqa: E402
from hydra_engine.intake.paths import IntakePaths  # noqa: E402


def _paths() -> IntakePaths:
    root = Path(tempfile.mkdtemp(prefix="intake-inventory-"))
    return IntakePaths(root=root, hydra=root / ".hydra-framework")


def _seed(paths: IntakePaths, rel: str, content: str) -> Path:
    path = paths.root / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    return path


class MigrationInventoryTests(unittest.TestCase):
    def test_missing_staging_root_reports_absence(self):
        paths = _paths()
        with mock.patch("hydra_engine.ports.git.tracked_files", return_value=[]):
            result = inventory.migration_inventory(paths)
        self.assertEqual(result["schema"], inventory.MIGRATION_INVENTORY_SCHEMA)
        self.assertFalse(result["exists"])
        self.assertEqual(result["totals"]["sources"], 0)
        self.assertTrue(any("create .migrations/" in note for note in result["notes"]))

    def test_classifies_staged_provider_and_ai_material(self):
        paths = _paths()
        _seed(paths, ".migrations/legacy-ai/AGENTS.md", "# Old agent rules\n")
        _seed(paths, ".migrations/legacy-ai/.claude/settings.json", "{}\n")
        _seed(paths, ".migrations/legacy-ai/prompts/system.md", "You are the old assistant.\n")
        _seed(paths, ".migrations/legacy-ai/tasks/board.md", "# Old board\n")
        _seed(paths, ".migrations/legacy-ai/.env", "TOKEN=example\n")

        with mock.patch(
            "hydra_engine.ports.git.tracked_files",
            return_value=[".migrations/legacy-ai/AGENTS.md"],
        ):
            result = inventory.migration_inventory(paths, "legacy-ai")

        self.assertEqual(result["totals"]["sources"], 1)
        source = result["sources"][0]
        self.assertEqual(source["slug"], "legacy-ai")
        self.assertEqual(source["files"], 5)
        self.assertEqual(source["tracked_files"], 1)
        self.assertEqual(source["untracked_files"], 4)
        self.assertEqual(source["classifications"]["provider-surface"], 2)
        self.assertEqual(source["classifications"]["provider-settings"], 1)
        self.assertEqual(source["classifications"]["ai-prompt-or-rules"], 2)
        self.assertEqual(source["classifications"]["task-or-session-state"], 1)
        self.assertEqual(source["classifications"]["credential-or-private-risk"], 1)

    def test_classifies_staged_hydra_project_without_promoting_it(self):
        paths = _paths()
        _seed(
            paths,
            ".migrations/hydra-projects/downstream/.hydra-framework/manifest.yaml",
            "seed_version: 0.1.0\n",
        )
        _seed(
            paths,
            ".migrations/hydra-projects/downstream/.hydra-framework/repo/knowledge-units/0001-test.md",
            "---\nhydra_id: hydra://knowledge-unit/downstream-test\nkind: knowledge-unit\n---\n# Test\n",
        )

        with mock.patch("hydra_engine.ports.git.tracked_files", return_value=[]):
            result = inventory.migration_inventory(paths, "hydra-projects")

        source = result["sources"][0]
        self.assertEqual(source["slug"], "hydra-projects")
        self.assertEqual(source["classifications"]["hydra-project"], 2)
        self.assertEqual(source["classifications"]["hydra-object"], 1)
        self.assertTrue(any("not canonical Hydra state" in note for note in result["notes"]))

    def test_unknown_slug_notes_no_staged_source(self):
        paths = _paths()
        paths.staging_root().mkdir(parents=True)
        with mock.patch("hydra_engine.ports.git.tracked_files", return_value=[]):
            result = inventory.migration_inventory(paths, "nope")
        self.assertEqual(result["totals"]["sources"], 0)
        self.assertTrue(any("no staged source found at .migrations/nope" in note for note in result["notes"]))

    def test_rejects_slug_that_escapes_the_staging_root(self):
        paths = _paths()
        with self.assertRaises(ValueError):
            inventory.migration_inventory(paths, "../outside")


if __name__ == "__main__":
    unittest.main()
