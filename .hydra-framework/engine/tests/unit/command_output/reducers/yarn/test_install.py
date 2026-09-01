"""Mirror tests for `hydra_engine.command_output.reducers.yarn.install`."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

_SRC = Path(__file__).resolve().parents[5] / "src"
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

from hydra_engine.command_output import shell  # noqa: E402
from hydra_engine.command_output.reducers.yarn import install  # noqa: E402


class YarnInstallReducerTests(unittest.TestCase):
    def test_matches_yarn_install(self):
        self.assertTrue(install.matches(shell.parse_command("yarn install --immutable")))


if __name__ == "__main__":
    unittest.main()

