"""Mirror test for `hydra_engine.wiki.paths`."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

_SRC = Path(__file__).resolve().parents[3] / "src"
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

from hydra_engine.wiki import paths  # noqa: E402


class WikiPathsTests(unittest.TestCase):
    def test_holds_root_and_project_wiki_verbatim(self):
        root = Path("/tmp/repo")
        project_wiki = Path("/tmp/repo/project-wiki")
        bundle = paths.WikiPaths(root=root, project_wiki=project_wiki)
        self.assertEqual(bundle.root, root)
        self.assertEqual(bundle.project_wiki, project_wiki)


if __name__ == "__main__":
    unittest.main()
