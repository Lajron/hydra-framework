"""Mirror test for `hydra_engine.intake.ledger`."""

from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

_SRC = Path(__file__).resolve().parents[3] / "src"
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

from hydra_engine.intake import ledger  # noqa: E402
from hydra_engine.intake.paths import IntakePaths  # noqa: E402
from hydra_engine.ports import clock as clock_port  # noqa: E402


def _paths() -> IntakePaths:
    root = Path(tempfile.mkdtemp(prefix="intake-ledger-"))
    return IntakePaths(root=root, hydra=root / ".hydra-framework")


def _seed(paths: IntakePaths, rel: str, content: str) -> Path:
    path = paths.root / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    return path


class MarkdownCellTests(unittest.TestCase):
    def test_escapes_pipes_and_collapses_newlines(self):
        self.assertEqual(ledger.markdown_cell("a\nb|c"), "a b\\|c")

    def test_blank_value_becomes_a_single_space(self):
        self.assertEqual(ledger.markdown_cell("  "), " ")


class MigrationLedgerStatusTests(unittest.TestCase):
    def test_is_read_only(self):
        paths = _paths()
        _seed(paths, ".migrations/legacy-ai/AGENTS.md", "# Old agent rules\n")

        with mock.patch("hydra_engine.ports.git.tracked_files", return_value=[]):
            status = ledger.migration_ledger_status(paths, "legacy-ai")

        self.assertEqual(status["schema"], ledger.MIGRATION_LEDGER_SCHEMA)
        self.assertEqual(status["source_path"], ".migrations/legacy-ai")
        self.assertEqual(
            status["planned_workspace"],
            f".hydra-framework/intake/migrations/{clock_port.today()}-legacy-ai",
        )
        self.assertEqual(status["existing_workspaces"], [])
        self.assertFalse((paths.root / ".hydra-framework/intake/migrations").exists())


class CreateMigrationLedgerTests(unittest.TestCase):
    def test_creates_ledger_from_staged_source(self):
        paths = _paths()
        _seed(paths, ".migrations/legacy-ai/AGENTS.md", "# Old agent rules\n")
        _seed(paths, ".migrations/legacy-ai/docs/guide.md", "# Guide\n")
        _seed(paths, ".migrations/legacy-ai/.env", "TOKEN=example\n")

        with mock.patch("hydra_engine.ports.git.tracked_files", return_value=[]):
            status = ledger.create_migration_ledger(paths, "legacy-ai")

        workspace = paths.root / ".hydra-framework/intake/migrations" / f"{clock_port.today()}-legacy-ai"
        self.assertEqual(
            status["created_workspace"],
            f".hydra-framework/intake/migrations/{clock_port.today()}-legacy-ai",
        )
        self.assertTrue((workspace / "README.md").exists())
        ledger_text = (workspace / "ledger.md").read_text(encoding="utf-8")
        self.assertIn(
            "| `.migrations/legacy-ai/AGENTS.md` | triage | TBD | pending | ai-prompt-or-rules, provider-surface |",
            ledger_text,
        )
        self.assertIn("| `.migrations/legacy-ai/docs/guide.md` | triage | TBD | pending | docs-or-wiki |", ledger_text)
        self.assertNotIn(".env", ledger_text)
        self.assertIn("grouped; risk classifications: credential-or-private-risk", ledger_text)
        self.assertIn("- Total items: 3", ledger_text)
        self.assertIn("- Pending: 3", ledger_text)

    def test_refuses_duplicate_workspace(self):
        paths = _paths()
        _seed(paths, ".migrations/legacy-ai/AGENTS.md", "# Old agent rules\n")
        _seed(
            paths,
            f".hydra-framework/intake/migrations/{clock_port.today()}-legacy-ai/ledger.md",
            "# existing\n",
        )

        with mock.patch("hydra_engine.ports.git.tracked_files", return_value=[]):
            with self.assertRaises(FileExistsError):
                ledger.create_migration_ledger(paths, "legacy-ai")

    def test_refuses_unknown_slug(self):
        paths = _paths()
        with mock.patch("hydra_engine.ports.git.tracked_files", return_value=[]):
            with self.assertRaises(ValueError):
                ledger.create_migration_ledger(paths, "nope")


if __name__ == "__main__":
    unittest.main()
