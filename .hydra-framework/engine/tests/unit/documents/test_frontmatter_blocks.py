"""Mirror test for `hydra_engine.documents.frontmatter_blocks`."""

from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

_SRC = Path(__file__).resolve().parents[3] / "src"
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

from hydra_engine.documents import frontmatter_blocks  # noqa: E402


class FrontmatterBlockTests(unittest.TestCase):
    def test_parses_frontmatter_block(self):
        root = Path(tempfile.mkdtemp(prefix="frontmatter-test-"))
        path = root / "doc.md"
        path.write_text("---\ntitle: Thing\nkind: knowledge-unit\n---\n\nbody\n", encoding="utf-8")
        data = frontmatter_blocks.markdown_frontmatter(path, root)
        self.assertEqual(data["title"], "Thing")
        self.assertEqual(data["kind"], "knowledge-unit")

    def test_no_frontmatter_returns_empty(self):
        root = Path(tempfile.mkdtemp(prefix="frontmatter-test-"))
        path = root / "doc.md"
        path.write_text("# Just a heading\n", encoding="utf-8")
        self.assertEqual(frontmatter_blocks.markdown_frontmatter(path, root), {})

    def test_unterminated_frontmatter_raises(self):
        root = Path(tempfile.mkdtemp(prefix="frontmatter-test-"))
        path = root / "doc.md"
        path.write_text("---\ntitle: Thing\n", encoding="utf-8")
        with self.assertRaises(frontmatter_blocks.HydraYamlError):
            frontmatter_blocks.markdown_frontmatter(path, root)


class PythonDocstringFrontmatterTests(unittest.TestCase):
    def _module(self, text: str) -> tuple[Path, Path]:
        root = Path(tempfile.mkdtemp(prefix="frontmatter-test-"))
        path = root / "module.py"
        path.write_text(text, encoding="utf-8")
        return path, root

    def test_parses_a_block_at_the_top_of_the_docstring(self):
        path, root = self._module('"""---\ntitle: Thing\nkind: engine-module\n---\n\nProse.\n"""\n')
        data = frontmatter_blocks.python_docstring_frontmatter(path, root)
        self.assertEqual(data["title"], "Thing")
        self.assertEqual(data["kind"], "engine-module")

    def test_an_ordinary_docstring_returns_empty(self):
        path, root = self._module('"""Just prose."""\n\nX = 1\n')
        self.assertEqual(frontmatter_blocks.python_docstring_frontmatter(path, root), {})

    def test_no_docstring_returns_empty(self):
        path, root = self._module("X = 1\n")
        self.assertEqual(frontmatter_blocks.python_docstring_frontmatter(path, root), {})

    def test_a_shebang_and_a_leading_comment_do_not_hide_the_block(self):
        # Read through `ast`, so Python's own parser decides where the
        # docstring starts rather than a second guess at the first line.
        path, root = self._module('#!/usr/bin/env python3\n# note\n"""---\ntitle: Thing\n---\n"""\n')
        self.assertEqual(frontmatter_blocks.python_docstring_frontmatter(path, root)["title"], "Thing")

    def test_unterminated_docstring_frontmatter_raises(self):
        path, root = self._module('"""---\ntitle: Thing\n"""\n')
        with self.assertRaises(frontmatter_blocks.HydraYamlError):
            frontmatter_blocks.python_docstring_frontmatter(path, root)

    def test_unparseable_python_raises_rather_than_reading_as_empty(self):
        path, root = self._module("def broken(:\n")
        with self.assertRaises(frontmatter_blocks.HydraYamlError):
            frontmatter_blocks.python_docstring_frontmatter(path, root)


class FirstDeclaredStringTests(unittest.TestCase):
    def test_returns_the_first_declared_spelling_in_order(self):
        self.assertEqual(frontmatter_blocks.first_declared_string({"name": "N"}, ("title", "name")), "N")
        self.assertEqual(
            frontmatter_blocks.first_declared_string({"title": "T", "name": "N"}, ("title", "name")), "T"
        )

    def test_absent_and_non_string_values_invent_nothing(self):
        self.assertEqual(frontmatter_blocks.first_declared_string({}, ("title",)), "")
        self.assertEqual(frontmatter_blocks.first_declared_string({"title": []}, ("title",)), "")


if __name__ == "__main__":
    unittest.main()
