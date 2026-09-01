"""Mirror tests for `hydra_engine.command_output.reducers.dotnet.test`."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

_SRC = Path(__file__).resolve().parents[5] / "src"
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

from hydra_engine.command_output import shell  # noqa: E402
from hydra_engine.command_output.reducers.dotnet import test  # noqa: E402


class DotnetTestReducerTests(unittest.TestCase):
    def test_matches_dotnet_test(self):
        self.assertTrue(test.matches(shell.parse_command("dotnet test --no-build")))


if __name__ == "__main__":
    unittest.main()

