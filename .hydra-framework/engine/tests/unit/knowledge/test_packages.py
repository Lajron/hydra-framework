"""Mirror test for `hydra_engine.knowledge.packages`."""

from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

_SRC = Path(__file__).resolve().parents[3] / "src"
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

from hydra_engine.knowledge import packages  # noqa: E402


class KnowledgePackageDiscoveryTests(unittest.TestCase):
    def test_discovers_packages_with_a_recognized_marker(self):
        root = Path(tempfile.mkdtemp(prefix="packages-test-"))
        hydra = root / ".hydra-framework"
        pkg_root = hydra / "repo/knowledge/knowledge-packages/example"
        pkg_root.mkdir(parents=True)
        (pkg_root / "overview.md").write_text("# Example\n", encoding="utf-8")
        (hydra / "repo/knowledge/knowledge-packages/templates").mkdir(parents=True)
        paths = packages.ContextCompilerPaths(root=root, hydra=hydra)
        discovered = packages.discover_knowledge_packages(paths)
        self.assertEqual([p.name for p in discovered], ["example"])

    def test_knowledge_package_root_for_path_ignores_templates(self):
        root = Path(tempfile.mkdtemp(prefix="packages-test-"))
        hydra = root / ".hydra-framework"
        packages_root = hydra / "repo/knowledge/knowledge-packages"
        packages_root.mkdir(parents=True)
        paths = packages.ContextCompilerPaths(root=root, hydra=hydra)
        nested = packages_root / "example" / "state.md"
        self.assertEqual(packages.knowledge_package_root_for_path(nested, paths), packages_root / "example")
        self.assertIsNone(packages.knowledge_package_root_for_path(packages_root / "templates" / "state.md", paths))


if __name__ == "__main__":
    unittest.main()
