"""Mirror test for `hydra_engine.documents.markdown`."""

from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

_SRC = Path(__file__).resolve().parents[3] / "src"
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

from hydra_engine.documents import markdown  # noqa: E402


class MarkdownTests(unittest.TestCase):
    def test_iter_markdown_files_skips_ignored_directories(self):
        root = Path(tempfile.mkdtemp(prefix="markdown-test-"))
        (root / "keep.md").write_text("# Keep\n", encoding="utf-8")
        (root / "node_modules").mkdir()
        (root / "node_modules" / "skip.md").write_text("# Skip\n", encoding="utf-8")
        files = markdown.iter_markdown_files(root)
        self.assertEqual([p.name for p in files], ["keep.md"])

    def test_strip_markdown_code_fences_blanks_fenced_content(self):
        text = "before\n```\nfenced hydra://knowledge-unit/x\n```\nafter\n"
        stripped = markdown.strip_markdown_code_fences(text)
        self.assertNotIn("fenced", stripped)
        self.assertIn("before", stripped)
        self.assertIn("after", stripped)

    def test_first_markdown_heading_returns_first_h1(self):
        root = Path(tempfile.mkdtemp(prefix="markdown-test-"))
        path = root / "doc.md"
        path.write_text("intro\n\n# The Title\n\nbody\n", encoding="utf-8")
        self.assertEqual(markdown.first_markdown_heading(path), "The Title")

    def test_first_markdown_heading_empty_when_absent(self):
        root = Path(tempfile.mkdtemp(prefix="markdown-test-"))
        path = root / "doc.md"
        path.write_text("no heading here\n", encoding="utf-8")
        self.assertEqual(markdown.first_markdown_heading(path), "")


if __name__ == "__main__":
    unittest.main()
