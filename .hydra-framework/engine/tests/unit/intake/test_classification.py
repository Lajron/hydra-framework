"""Mirror test for `hydra_engine.intake.classification`."""

from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

_SRC = Path(__file__).resolve().parents[3] / "src"
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

from hydra_engine.intake import classification  # noqa: E402


class ReadMigrationFilePeekTests(unittest.TestCase):
    def setUp(self) -> None:
        self.root = Path(tempfile.mkdtemp(prefix="intake-classification-"))

    def test_reads_text_file_contents(self):
        path = self.root / "notes.md"
        path.write_text("hello\n", encoding="utf-8")
        self.assertEqual(classification.read_migration_file_peek(path), "hello\n")

    def test_binary_file_with_null_byte_returns_empty(self):
        path = self.root / "binary.dat"
        path.write_bytes(b"\x00\x01\x02")
        self.assertEqual(classification.read_migration_file_peek(path), "")

    def test_missing_file_returns_empty(self):
        self.assertEqual(classification.read_migration_file_peek(self.root / "missing.md"), "")


class ClassifyMigrationFileTests(unittest.TestCase):
    def setUp(self) -> None:
        self.root = Path(tempfile.mkdtemp(prefix="intake-classify-"))

    def _seed(self, rel: str, content: str = "x\n") -> Path:
        path = self.root / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
        return path

    def test_provider_surface_and_ai_rules(self):
        path = self._seed("AGENTS.md", "# Old agent rules\n")
        tags = classification.classify_migration_file(path, self.root)
        self.assertIn("provider-surface", tags)
        self.assertIn("ai-prompt-or-rules", tags)

    def test_provider_settings_json_under_provider_dir(self):
        path = self._seed(".claude/settings.json", "{}\n")
        tags = classification.classify_migration_file(path, self.root)
        self.assertIn("provider-surface", tags)
        self.assertIn("provider-settings", tags)

    def test_credential_risk_from_env_file(self):
        path = self._seed(".env", "TOKEN=example\n")
        tags = classification.classify_migration_file(path, self.root)
        self.assertIn("credential-or-private-risk", tags)

    def test_machine_local_risk_from_git_dir(self):
        path = self._seed(".git/config", "x\n")
        tags = classification.classify_migration_file(path, self.root)
        self.assertIn("machine-local-risk", tags)

    def test_hydra_project_and_hydra_object(self):
        path = self._seed(
            ".hydra-framework/repo/knowledge-units/0001-test.md",
            "---\nhydra_id: hydra://knowledge-unit/downstream-test\nkind: knowledge-unit\n---\n# Test\n",
        )
        tags = classification.classify_migration_file(path, self.root)
        self.assertIn("hydra-project", tags)
        self.assertIn("hydra-object", tags)

    def test_task_or_session_state_from_path_words(self):
        path = self._seed("tasks/board.md", "# Old board\n")
        tags = classification.classify_migration_file(path, self.root)
        self.assertIn("task-or-session-state", tags)

    def test_docs_or_wiki_from_path_words(self):
        path = self._seed("docs/guide.md", "# Guide\n")
        tags = classification.classify_migration_file(path, self.root)
        self.assertIn("docs-or-wiki", tags)

    def test_raw_source_material_for_binary_suffix(self):
        path = self._seed("diagram.png", "x")
        tags = classification.classify_migration_file(path, self.root)
        self.assertIn("raw-source-material", tags)

    def test_untagged_file_falls_back_to_source_material(self):
        path = self._seed("plain.xyz", "x\n")
        tags = classification.classify_migration_file(path, self.root)
        self.assertEqual(tags, ["source-material"])


if __name__ == "__main__":
    unittest.main()
