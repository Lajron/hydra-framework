"""Mirror test for `hydra_engine.providers.paths`."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

_SRC = Path(__file__).resolve().parents[3] / "src"
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

from hydra_engine.providers import paths  # noqa: E402


class ProvidersPathsTests(unittest.TestCase):
    def setUp(self) -> None:
        self.root = Path("/tmp/repo")
        self.bundle = paths.ProvidersPaths(root=self.root, hydra=self.root / ".hydra-framework")

    def test_capability_map_path(self):
        self.assertEqual(
            self.bundle.capability_map_path("claude"),
            self.root / ".hydra-framework/adapters/providers/claude/capability-map.yaml",
        )

    def test_skills_and_agents_roots(self):
        self.assertEqual(self.bundle.skills_root(), self.root / ".hydra-framework/capabilities/skills")
        self.assertEqual(self.bundle.agents_root(), self.root / ".hydra-framework/capabilities/agents")

    def test_canonical_module_dir(self):
        self.assertEqual(self.bundle.canonical_module_dir("agent"), self.root / ".hydra-framework/capabilities/agents")
        self.assertEqual(self.bundle.canonical_module_dir("skill"), self.root / ".hydra-framework/capabilities/skills")
        self.assertEqual(self.bundle.canonical_module_dir("legacy-command"), self.root / ".hydra-framework/capabilities/skills")


if __name__ == "__main__":
    unittest.main()
