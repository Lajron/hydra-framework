"""Mirror test for `hydra_engine.wiki.scaffold`."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

_SRC = Path(__file__).resolve().parents[3] / "src"
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

from hydra_engine.wiki import scaffold  # noqa: E402


class WikiHomePageTextTests(unittest.TestCase):
    def test_includes_title_and_sources_link(self):
        text = scaffold.wiki_home_page_text("Demo Project")
        self.assertTrue(text.startswith("# Demo Project\n"))
        self.assertIn("[[sources]]", text)


class WikiSourcesPageTextTests(unittest.TestCase):
    def test_includes_title_in_heading(self):
        text = scaffold.wiki_sources_page_text("Demo Project")
        self.assertTrue(text.startswith("# Demo Project Sources\n"))


if __name__ == "__main__":
    unittest.main()
