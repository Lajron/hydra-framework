"""Mirror tests for `hydra_engine.command_output.shell`."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

_SRC = Path(__file__).resolve().parents[3] / "src"
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

from hydra_engine.command_output import shell  # noqa: E402


class ShellParsingTests(unittest.TestCase):
    def test_skips_env_and_carrier_segments(self):
        parsed = shell.parse_command("cd app && TOKEN=secret dotnet build App.sln")
        self.assertEqual(parsed.head, "dotnet")
        self.assertEqual(parsed.significant_tokens[:2], ("dotnet", "build"))

    def test_pipeline_stays_inside_segment(self):
        self.assertEqual(shell.split_top_level_segments("rg foo | head -20"), (("rg", "foo", "|", "head", "-20"),))

    def test_git_subcommand_skips_options_with_values(self):
        self.assertEqual(shell.git_subcommand(("git", "-C", "repo", "status", "--short")), "status")


if __name__ == "__main__":
    unittest.main()

