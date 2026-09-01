"""Mirror tests for `hydra_engine.command_output.reducers.yarn.build`."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

_SRC = Path(__file__).resolve().parents[5] / "src"
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

from hydra_engine.command_output import shell  # noqa: E402
from hydra_engine.command_output.reducers.yarn import build  # noqa: E402


class YarnBuildReducerTests(unittest.TestCase):
    def test_matches_yarn_build(self):
        self.assertTrue(build.matches(shell.parse_command("yarn build")))


if __name__ == "__main__":
    unittest.main()

