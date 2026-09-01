"""Mirror test for `hydra_engine.wiki.links`."""

from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

_SRC = Path(__file__).resolve().parents[3] / "src"
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

from hydra_engine.wiki import links  # noqa: E402


class MarkdownLinkTargetTests(unittest.TestCase):
    def test_strips_angle_brackets(self):
        self.assertEqual(links.markdown_link_target("<./foo.md>"), "./foo.md")

    def test_drops_trailing_title_when_not_a_relative_path(self):
        self.assertEqual(links.markdown_link_target('foo.md "title"'), "foo.md")

    def test_unquotes_percent_encoding(self):
        self.assertEqual(links.markdown_link_target("a%20b.md"), "a b.md")


class ValidateMarkdownLinksTests(unittest.TestCase):
    def test_reports_missing_relative_link(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "page.md").write_text("[broken](missing.md)\n", encoding="utf-8")
            errors = links.validate_markdown_links(root, root)
        self.assertEqual(len(errors), 1)
        self.assertIn("missing.md", errors[0])

    def test_existing_relative_link_is_not_reported(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "target.md").write_text("# Target\n", encoding="utf-8")
            (root / "page.md").write_text("[ok](target.md)\n", encoding="utf-8")
            errors = links.validate_markdown_links(root, root)
        self.assertEqual(errors, [])

    def test_scheme_links_are_ignored(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "page.md").write_text("[ext](https://example.com/x)\n", encoding="utf-8")
            errors = links.validate_markdown_links(root, root)
        self.assertEqual(errors, [])


class ObsidianLinkTargetTests(unittest.TestCase):
    def test_strips_alias_and_heading_fragment(self):
        self.assertEqual(links.obsidian_link_target("page#section|Alias"), "page")


class ObsidianLinkExistsTests(unittest.TestCase):
    def test_finds_page_by_bare_name_anywhere_under_wiki_root(self):
        with tempfile.TemporaryDirectory() as tmp:
            wiki_root = Path(tmp)
            (wiki_root / "sub").mkdir()
            (wiki_root / "sub" / "target.md").write_text("# Target\n", encoding="utf-8")
            self.assertTrue(links.obsidian_link_exists("target", wiki_root, wiki_root))

    def test_missing_page_is_reported_as_absent(self):
        with tempfile.TemporaryDirectory() as tmp:
            wiki_root = Path(tmp)
            self.assertFalse(links.obsidian_link_exists("nope", wiki_root, wiki_root))


class ValidateObsidianLinksTests(unittest.TestCase):
    def test_reports_missing_wiki_root(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            missing_root = root / "does-not-exist"
            errors = links.validate_obsidian_links(missing_root, root)
        self.assertEqual(len(errors), 1)
        self.assertIn("wiki root does not exist", errors[0])

    def test_reports_missing_wiki_link(self):
        with tempfile.TemporaryDirectory() as tmp:
            wiki_root = Path(tmp)
            (wiki_root / "home.md").write_text("[[nope]]\n", encoding="utf-8")
            errors = links.validate_obsidian_links(wiki_root, wiki_root)
        self.assertEqual(len(errors), 1)
        self.assertIn("nope", errors[0])


class ValidateWikiTests(unittest.TestCase):
    def test_combines_markdown_and_obsidian_errors(self):
        with tempfile.TemporaryDirectory() as tmp:
            wiki_root = Path(tmp)
            wiki_root.joinpath("home.md").write_text("[md](missing.md)\n\n[[missing-wiki]]\n", encoding="utf-8")
            errors = links.validate_wiki(wiki_root, wiki_root)
        self.assertEqual(len(errors), 2)

    def test_rejects_traversal_markdown_links_but_allows_root_relative_links(self):
        with tempfile.TemporaryDirectory() as tmp:
            workspace = Path(tmp)
            root = workspace / "wiki"
            root.mkdir()
            (workspace / "outside.md").write_text("# Outside\n", encoding="utf-8")
            (root / "target.md").write_text("# Target\n", encoding="utf-8")
            (root / "page.md").write_text(
                "[bad](../outside.md)\n"
                "[root](/target.md)\n"
                "[external](https://example.com)\n"
                "[section](#part)\n",
                encoding="utf-8",
            )
            errors = links.validate_wiki(root, root)
        self.assertEqual(len(errors), 1)
        self.assertEqual(errors[0].code, "markdown-link-paths")
        self.assertIn("../outside.md", errors[0])


if __name__ == "__main__":
    unittest.main()
