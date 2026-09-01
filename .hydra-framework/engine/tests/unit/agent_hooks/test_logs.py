"""Mirror test for `hydra_engine.agent_hooks.logs`.

Moved from `scripts/tests/test_hydra.py`'s `LogSummaryTests`.
"""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

_SRC = Path(__file__).resolve().parents[3] / "src"
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

from hydra_engine.agent_hooks import logs  # noqa: E402


class LogSummaryTests(unittest.TestCase):
    def test_keeps_error_lines_and_marks_omissions(self):
        lines = [f"progress {index}" for index in range(60)]
        lines[30] = "ERROR: something failed at line 12"
        summary = logs.summarize_log_text("\n".join(lines), 10)
        self.assertTrue(any("ERROR: something failed" in line for line in summary))
        self.assertTrue(any("omitted" in line for line in summary))

    def test_empty_log_returns_empty(self):
        self.assertEqual(logs.summarize_log_text("", 10), [])

    def test_falls_back_to_head_and_tail_without_matches(self):
        text = "\n".join(f"line {index}" for index in range(40))
        summary = logs.summarize_log_text(text, 6)
        self.assertTrue(summary)
        self.assertLessEqual(len([line for line in summary if line.startswith("L")]), 6)

    def test_selected_log_indexes_ignores_noise_around_matches(self):
        lines = ["10% downloading", "ERROR: boom", "10% downloading"]
        selected = logs.selected_log_indexes(lines, 10)
        self.assertIn(1, selected)
        self.assertNotIn(0, selected)
        self.assertNotIn(2, selected)


if __name__ == "__main__":
    unittest.main()
