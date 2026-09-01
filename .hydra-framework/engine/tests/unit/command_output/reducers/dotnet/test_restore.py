"""Mirror tests for `hydra_engine.command_output.reducers.dotnet.restore`."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

_SRC = Path(__file__).resolve().parents[5] / "src"
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

from hydra_engine.command_output import shell  # noqa: E402
from hydra_engine.command_output.reducers.dotnet import restore  # noqa: E402


class DotnetRestoreReducerTests(unittest.TestCase):
    def test_matches_dotnet_restore(self):
        self.assertTrue(restore.matches(shell.parse_command("dotnet restore")))


if __name__ == "__main__":
    unittest.main()

