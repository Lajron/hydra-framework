"""Mirror tests for `hydra_engine.command_output.reducers.git.diff`."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

_SRC = Path(__file__).resolve().parents[5] / "src"
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

from hydra_engine.command_output import shell  # noqa: E402
from hydra_engine.command_output.reducers.git import diff  # noqa: E402


class GitDiffReducerTests(unittest.TestCase):
    def test_matches_git_diff(self):
        self.assertTrue(diff.matches(shell.parse_command("git diff -- README.md")))


if __name__ == "__main__":
    unittest.main()

