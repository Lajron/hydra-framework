"""Mirror tests for `hydra_engine.command_output.model`."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

_SRC = Path(__file__).resolve().parents[3] / "src"
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

from hydra_engine.command_output import model  # noqa: E402


class CommandOutputModelTests(unittest.TestCase):
    def test_command_output_counts_lines_and_chars(self):
        output = model.CommandOutput("manual", "", "x", ".", 0, "a\nb\n")
        self.assertEqual(output.line_count, 2)
        self.assertEqual(output.char_count, 4)

    def test_none_reducer_is_not_a_real_reducer(self):
        reduction = model.Reduction("s", "manual", "", "", ".", 0, "unknown", "none", "1", "", (), 0, 0, 0, 0)
        self.assertFalse(reduction.has_reducer)


if __name__ == "__main__":
    unittest.main()

