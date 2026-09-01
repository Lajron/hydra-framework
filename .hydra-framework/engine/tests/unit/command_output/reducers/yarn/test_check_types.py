"""Mirror tests for `hydra_engine.command_output.reducers.yarn.check_types`."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

_SRC = Path(__file__).resolve().parents[5] / "src"
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

from hydra_engine.command_output import shell  # noqa: E402
from hydra_engine.command_output.reducers.yarn import check_types  # noqa: E402


class YarnCheckTypesReducerTests(unittest.TestCase):
    def test_matches_yarn_check_types(self):
        self.assertTrue(check_types.matches(shell.parse_command("yarn check-types")))


if __name__ == "__main__":
    unittest.main()

