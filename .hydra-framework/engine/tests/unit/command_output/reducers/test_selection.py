"""Mirror tests for `hydra_engine.command_output.reducers.selection`."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

_SRC = Path(__file__).resolve().parents[4] / "src"
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

from hydra_engine.command_output.reducers import selection  # noqa: E402


class SelectionTests(unittest.TestCase):
    def test_repeated_warnings_are_collapsed(self):
        lines = ["warning abc 1", "warning abc 2", "error TS1001: bad"]
        selected = selection.important_lines("\n".join(lines), "yarn-check-types", 10)
        self.assertEqual(sum(1 for line in selected if "warning abc" in line), 1)
        self.assertTrue(any("TS1001" in line for line in selected))

    def test_fallback_keeps_head_and_tail(self):
        self.assertEqual(selection.fallback_indexes(["a", "b", "c", "d"], 2), [0, 3])


if __name__ == "__main__":
    unittest.main()

