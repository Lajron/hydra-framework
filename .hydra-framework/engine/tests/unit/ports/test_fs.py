"""Mirror test for `hydra_engine.ports.fs` (the append-only amendment).

The interleaving test injects the exact competing-writer race deterministically
via the `_before_append` seam instead of threads: see `documents/tokens.py`'s
docstring and `test_tokens.py` for the same pattern applied to `write_text`.
"""

from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

_SRC = Path(__file__).resolve().parents[3] / "src"
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

from hydra_engine.ports import fs  # noqa: E402


def _path() -> Path:
    root = Path(tempfile.mkdtemp(prefix="ports-fs-"))
    return root / "sub" / "state.jsonl"


class AppendLineTests(unittest.TestCase):
    def test_append_line_creates_missing_parent_and_file(self):
        path = _path()
        fs.append_line(path, "one")
        self.assertEqual(path.read_text(encoding="utf-8"), "one\n")

    def test_append_line_does_not_duplicate_an_existing_trailing_newline(self):
        path = _path()
        fs.append_line(path, "one\n")
        fs.append_line(path, "two")
        self.assertEqual(path.read_text(encoding="utf-8"), "one\ntwo\n")

    def test_repeated_appends_accumulate_in_order(self):
        path = _path()
        for value in ("a", "b", "c"):
            fs.append_line(path, value)
        self.assertEqual(path.read_text(encoding="utf-8").splitlines(), ["a", "b", "c"])

    def test_competing_append_injected_between_open_and_write_does_not_corrupt_either_line(self):
        # Reproduces two processes racing `append_line` on the same path with
        # zero threads: the seam runs a synchronous competing append after
        # this call has opened the file but before it has written its line.
        path = _path()
        fs.append_line(path, "first")

        def _competing_append(_path: Path) -> None:
            with mock.patch.object(fs, "_before_append", None):
                fs.append_line(path, "second")

        with mock.patch.object(fs, "_before_append", _competing_append):
            fs.append_line(path, "third")

        self.assertEqual(path.read_text(encoding="utf-8").splitlines(), ["first", "second", "third"])


class CreateExclusiveTests(unittest.TestCase):
    def test_create_exclusive_writes_content_when_absent(self):
        path = _path()
        self.assertTrue(fs.create_exclusive(path, "content\n"))
        self.assertEqual(path.read_text(encoding="utf-8"), "content\n")

    def test_create_exclusive_refuses_and_leaves_existing_content_untouched(self):
        path = _path()
        fs.create_exclusive(path, "original\n")
        self.assertFalse(fs.create_exclusive(path, "clobber\n"))
        self.assertEqual(path.read_text(encoding="utf-8"), "original\n")


if __name__ == "__main__":
    unittest.main()
