"""wiki-cluster goldens: validate-wiki, wiki scaffold."""

from __future__ import annotations

import unittest

from .fixtures import assert_golden, run_golden


class WikiGoldenTests(unittest.TestCase):
    def test_validate_wiki_happy_path(self):
        outcome = run_golden(["validate-wiki"], extra_fixture={"project-wiki/.gitkeep": ""})
        assert_golden(self, "wiki-validate-wiki", outcome)

    def test_validate_wiki_broken_markdown_link(self):
        outcome = run_golden(
            ["validate-wiki"],
            extra_fixture={"project-wiki/home.md": "[broken](missing.md)\n"},
        )
        assert_golden(self, "wiki-validate-wiki-broken-markdown-link", outcome)

    def test_validate_wiki_broken_obsidian_link(self):
        outcome = run_golden(
            ["validate-wiki"],
            extra_fixture={"project-wiki/home.md": "[[missing-page]]\n"},
        )
        assert_golden(self, "wiki-validate-wiki-broken-obsidian-link", outcome)

    def test_validate_wiki_missing_wiki_root(self):
        """No `project-wiki/` at all: `validate_obsidian_links`'s
        does-not-exist branch (`validate_markdown_links` finds nothing to
        walk and reports no errors of its own)."""
        outcome = run_golden(["validate-wiki"])
        assert_golden(self, "wiki-validate-wiki-missing-root", outcome)

    def test_wiki_scaffold_happy_path(self):
        outcome = run_golden(["wiki", "scaffold", "demo-project"])
        assert_golden(self, "wiki-scaffold", outcome)

    def test_wiki_scaffold_refuses_existing_without_force(self):
        outcome = run_golden(
            ["wiki", "scaffold", "demo-project"],
            extra_fixture={"project-wiki/demo-project/home.md": "# Existing\n"},
        )
        assert_golden(self, "wiki-scaffold-refuses-existing", outcome)

    def test_wiki_scaffold_force_overwrites_existing(self):
        outcome = run_golden(
            ["wiki", "scaffold", "demo-project", "--force"],
            extra_fixture={"project-wiki/demo-project/home.md": "# Existing\n"},
        )
        assert_golden(self, "wiki-scaffold-force-overwrites", outcome)


if __name__ == "__main__":
    unittest.main()
