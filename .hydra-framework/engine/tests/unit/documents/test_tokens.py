"""Mirror test for `hydra_engine.documents.tokens`."""

from __future__ import annotations

import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

_SRC = Path(__file__).resolve().parents[3] / "src"
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

from hydra_engine.documents import tokens  # noqa: E402


class TokenShapeTests(unittest.TestCase):
    def test_yaml_scalar_strips_matching_quotes(self):
        self.assertEqual(tokens.yaml_scalar('"quoted"'), "quoted")
        self.assertEqual(tokens.yaml_scalar("'quoted'"), "quoted")
        self.assertEqual(tokens.yaml_scalar("bare"), "bare")

    def test_reject_unsupported_yaml_flags_anchors_aliases_and_block_scalars(self):
        root = Path("/repo")
        path = root / "obj.yaml"
        with self.assertRaises(tokens.HydraYamlError):
            tokens.reject_unsupported_yaml(path, 1, "&anchor", root)
        with self.assertRaises(tokens.HydraYamlError):
            tokens.reject_unsupported_yaml(path, 1, "*anchor", root)
        with self.assertRaises(tokens.HydraYamlError):
            tokens.reject_unsupported_yaml(path, 1, "|", root)
        with self.assertRaises(tokens.HydraYamlError):
            tokens.reject_unsupported_yaml(path, 1, '"unterminated', root)
        tokens.reject_unsupported_yaml(path, 1, "fine", root)


class PathDisplayTests(unittest.TestCase):
    def test_is_relative_to_and_display_path(self):
        root = Path(__file__).resolve().parents[1]
        inside = Path(__file__).resolve()
        self.assertTrue(tokens.is_relative_to(inside, root))
        self.assertFalse(tokens.is_relative_to(Path("/nonexistent-root"), root))
        self.assertEqual(tokens.display_path(inside, root), inside.relative_to(root).as_posix())

    def test_display_path_falls_back_to_str_outside_root(self):
        outside = Path("/definitely/outside/this/tree.md")
        root = Path(__file__).resolve().parents[1]
        self.assertEqual(tokens.display_path(outside, root), str(outside))


class PathCitationTests(unittest.TestCase):
    def setUp(self):
        self.repo_root = Path(tempfile.mkdtemp(prefix="cited-path-test-"))
        (self.repo_root / ".hydra-framework").mkdir()
        (self.repo_root / ".hydra-framework/real.md").write_text("x", encoding="utf-8")
        self.citation_dir = self.repo_root / "package"
        self.citation_dir.mkdir()

    def test_brace_set_expands_each_option(self):
        self.assertEqual(sorted(tokens.expand_brace_sets("{a,b}/config.yaml")), ["a/config.yaml", "b/config.yaml"])

    def test_existing_repo_root_relative_path_is_not_missing(self):
        self.assertFalse(tokens.cited_source_path_missing(".hydra-framework/real.md", self.citation_dir, self.repo_root))

    def test_missing_repo_root_relative_path_is_missing(self):
        self.assertTrue(tokens.cited_source_path_missing(".hydra-framework/nope.md", self.citation_dir, self.repo_root))

    def test_dot_slash_resolves_relative_to_the_citation_directory(self):
        (self.citation_dir / "local.md").write_text("x", encoding="utf-8")
        self.assertFalse(tokens.cited_source_path_missing("./local.md", self.citation_dir, self.repo_root))
        self.assertTrue(tokens.cited_source_path_missing("./missing.md", self.citation_dir, self.repo_root))

    def test_non_path_prose_with_a_slash_is_not_treated_as_missing(self):
        self.assertFalse(tokens.cited_source_path_missing("GET /api/foo", self.citation_dir, self.repo_root))

    def test_brace_set_is_missing_if_any_option_is_missing(self):
        (self.repo_root / ".hydra-framework/a.md").write_text("x", encoding="utf-8")
        self.assertTrue(tokens.cited_source_path_missing(".hydra-framework/{a,b}.md", self.citation_dir, self.repo_root))

    def test_glob_resolves_against_any_match(self):
        self.assertFalse(tokens.cited_source_path_missing(".hydra-framework/*.md", self.citation_dir, self.repo_root))

    def test_trailing_slash_requires_a_directory(self):
        self.assertTrue(tokens.cited_source_path_missing(".hydra-framework/real.md/", self.citation_dir, self.repo_root))


class WriteTextTests(unittest.TestCase):
    def setUp(self):
        self.root = Path(tempfile.mkdtemp(prefix="write-text-test-"))
        self.target = self.root / "sub" / "file.txt"

    def test_write_text_creates_missing_parents_and_content(self):
        tokens.write_text(self.target, "hello\n")
        self.assertEqual(self.target.read_text(encoding="utf-8"), "hello\n")

    def test_write_text_replaces_existing_content_wholesale(self):
        tokens.write_text(self.target, "first\n")
        tokens.write_text(self.target, "second\n")
        self.assertEqual(self.target.read_text(encoding="utf-8"), "second\n")

    def test_write_text_leaves_no_tmp_file_behind_on_success(self):
        tokens.write_text(self.target, "hello\n")
        leftovers = list(self.target.parent.glob(".*.hydra-tmp-*"))
        self.assertEqual(leftovers, [])

    def test_crash_between_temp_write_and_replace_leaves_target_untouched(self):
        # Reproduces a process dying mid-write with zero threads: the seam
        # raises at the exact point after the temp file is fully written but
        # before `os.replace` swaps it in.
        tokens.write_text(self.target, "original\n")

        def _crash(_path: Path) -> None:
            raise RuntimeError("simulated crash before replace")

        with mock.patch.object(tokens, "_before_replace", _crash):
            with self.assertRaises(RuntimeError):
                tokens.write_text(self.target, "new\n")

        self.assertEqual(self.target.read_text(encoding="utf-8"), "original\n")
        leftovers = list(self.target.parent.glob(".*.hydra-tmp-*"))
        self.assertEqual(leftovers, [])

    def test_competing_write_injected_before_replace_never_produces_torn_content(self):
        # Reproduces two processes racing `write_text` on the same path: the
        # seam runs a synchronous competing write, under a different pid so
        # its temp file does not collide with this call's own, after this
        # call's temp file is complete but before its replace. The reader
        # only ever sees one writer's full content, never a mix of both.
        tokens.write_text(self.target, "original\n")

        def _competing_write(_path: Path) -> None:
            with mock.patch.object(tokens, "_before_replace", None), mock.patch("os.getpid", return_value=os.getpid() + 1):
                tokens.write_text(self.target, "competing\n")

        with mock.patch.object(tokens, "_before_replace", _competing_write):
            tokens.write_text(self.target, "mine\n")

        self.assertIn(self.target.read_text(encoding="utf-8"), ("competing\n", "mine\n"))


if __name__ == "__main__":
    unittest.main()
