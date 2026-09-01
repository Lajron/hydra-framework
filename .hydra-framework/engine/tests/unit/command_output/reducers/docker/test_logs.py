"""Mirror tests for `hydra_engine.command_output.reducers.docker.logs`."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

_SRC = Path(__file__).resolve().parents[5] / "src"
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

from hydra_engine.command_output import shell  # noqa: E402
from hydra_engine.command_output.reducers.docker import logs  # noqa: E402


class DockerLogsReducerTests(unittest.TestCase):
    def test_matches_docker_logs(self):
        self.assertTrue(logs.matches(shell.parse_command("docker logs api")))


if __name__ == "__main__":
    unittest.main()

