"""Mirror tests for `hydra_engine.command_output.reducers.curl.request`."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

_SRC = Path(__file__).resolve().parents[5] / "src"
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

from hydra_engine.command_output import shell  # noqa: E402
from hydra_engine.command_output.reducers.curl import request  # noqa: E402


class CurlRequestReducerTests(unittest.TestCase):
    def test_matches_curl(self):
        self.assertTrue(request.matches(shell.parse_command("curl -i https://example.test")))


if __name__ == "__main__":
    unittest.main()

