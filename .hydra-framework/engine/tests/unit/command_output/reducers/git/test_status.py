"""Mirror tests for `hydra_engine.command_output.reducers.git.status`."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

_SRC = Path(__file__).resolve().parents[5] / "src"
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

from hydra_engine.command_output import shell  # noqa: E402
from hydra_engine.command_output.reducers.git import status  # noqa: E402


class GitStatusReducerTests(unittest.TestCase):
    def test_matches_git_status(self):
        self.assertTrue(status.matches(shell.parse_command("git -C repo status --short")))


if __name__ == "__main__":
    unittest.main()

