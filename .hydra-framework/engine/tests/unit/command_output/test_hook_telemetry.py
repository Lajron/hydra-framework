"""Mirror tests for `hydra_engine.command_output.hook_telemetry`."""

from __future__ import annotations

import argparse
import sys
import tempfile
import unittest
from pathlib import Path

_SRC = Path(__file__).resolve().parents[3] / "src"
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

from hydra_engine.agent_hooks.paths import AgentHooksPaths  # noqa: E402
from hydra_engine.command_output import hook_telemetry  # noqa: E402
from hydra_engine.telemetry import writer  # noqa: E402


def _paths() -> AgentHooksPaths:
    root = Path(tempfile.mkdtemp(prefix="command-output-hook-telemetry-"))
    return AgentHooksPaths(root=root, local=root / ".hydra-framework.local")


class HookTelemetryTests(unittest.TestCase):
    def test_records_claude_reducer_event(self):
        paths = _paths()
        args = argparse.Namespace(config=None, max_lines=None)
        reduction = hook_telemetry.record_claude_capture(
            args,
            paths,
            {"session_id": "s1"},
            "dotnet build",
            "A.cs(1,1): error CS1001: bad\nBuild FAILED.\n",
            1,
        )
        self.assertEqual(reduction.family, "dotnet-build")
        rows = list(writer.iter_event_rows(paths.local))
        self.assertEqual(rows[0]["event_kind"], "command_output.reducer_outcome")
        self.assertEqual(rows[0]["command_family"], "dotnet-build")

    def test_records_codex_reducer_event_through_provider_neutral_helper(self):
        paths = _paths()
        args = argparse.Namespace(config=None, max_lines=None)
        reduction = hook_telemetry.record_provider_capture(
            args,
            paths,
            "codex",
            {"session_id": "s1"},
            "dotnet build",
            "A.cs(1,1): error CS1001: bad\nBuild FAILED.\n",
            1,
        )
        self.assertEqual(reduction.family, "dotnet-build")
        rows = list(writer.iter_event_rows(paths.local))
        self.assertEqual(rows[0]["event_kind"], "command_output.reducer_outcome")
        self.assertEqual(rows[0]["provider"], "codex")
        self.assertEqual(rows[0]["command_family"], "dotnet-build")


if __name__ == "__main__":
    unittest.main()
