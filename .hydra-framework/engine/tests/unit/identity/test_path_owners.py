"""Mirror test for `hydra_engine.identity.path_owners`."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

_SRC = Path(__file__).resolve().parents[3] / "src"
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

from hydra_engine.identity import path_owners  # noqa: E402


class DirectoryOwnerTests(unittest.TestCase):
    def test_matches_the_most_specific_registered_prefix(self):
        self.assertEqual(
            path_owners.directory_owner("repo/knowledge/example.md"),
            "Canonical repository-specific facts, conventions, and flat knowledge.",
        )
        self.assertEqual(
            path_owners.directory_owner("repo/README.md"),
            "Canonical repository-specific facts, conventions, and procedures.",
        )

    def test_exact_prefix_match(self):
        self.assertIsNotNone(path_owners.directory_owner("scripts"))

    def test_no_registered_owner_returns_none(self):
        self.assertIsNone(path_owners.directory_owner("manifest.yaml"))
        self.assertIsNone(path_owners.directory_owner("unregistered-top-level/file.md"))


class ProviderRootDeclarationTests(unittest.TestCase):
    def test_generated_skill_directory(self):
        declaration = path_owners.provider_root_declaration(".claude/skills/deploy/skill.md")
        self.assertEqual(declaration.status, "generated")

    def test_authored_settings_file(self):
        declaration = path_owners.provider_root_declaration(".claude/settings.json")
        self.assertEqual(declaration.status, "authored")

    def test_undeclared_provider_path_returns_none(self):
        self.assertIsNone(path_owners.provider_root_declaration(".claude/README.md"))
        self.assertIsNone(path_owners.provider_root_declaration("some/other/path.md"))


if __name__ == "__main__":
    unittest.main()
