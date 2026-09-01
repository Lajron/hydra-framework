"""Mirror tests for `hydra_engine.command_output.adapters`."""

from __future__ import annotations

import argparse
import json
import sys
import tempfile
import unittest
from pathlib import Path

_SRC = Path(__file__).resolve().parents[3] / "src"
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

from hydra_engine.agent_hooks.paths import AgentHooksPaths  # noqa: E402
from hydra_engine.command_output import adapters  # noqa: E402
from hydra_engine.telemetry import writer  # noqa: E402


def _paths() -> AgentHooksPaths:
    root = Path(tempfile.mkdtemp(prefix="command-output-adapters-"))
    return AgentHooksPaths(root=root, local=root / ".hydra-framework.local")


class CommandOutputAdapterTests(unittest.TestCase):
    def test_extracts_combined_bash_output(self):
        output, exit_code = adapters.bash_output_from_response({"stdout": "out", "stderr": "err", "exit_code": 1})
        self.assertEqual(output, "out\nerr")
        self.assertEqual(exit_code, 1)

    def test_claude_hook_replaces_large_known_success(self):
        args = argparse.Namespace(config=None, large_log_lines=1, large_log_chars=None)
        payload = {
            "tool_name": "Bash",
            "tool_input": {"command": "dotnet build"},
            "tool_response": {"stdout": "A.cs(1,1): error CS1001: bad\nBuild FAILED.\n", "exit_code": 0},
            "session_id": "s1",
        }
        feedback = adapters.claude_command_output_hook(args, _paths(), json.dumps(payload))
        self.assertEqual(feedback.exit_code, 0)
        self.assertIn("updatedToolOutput", feedback.stdout)
        self.assertIn("dotnet-build", feedback.stdout)

    def test_claude_hook_ignores_large_unknown_success(self):
        args = argparse.Namespace(config=None, large_log_lines=1, large_log_chars=None)
        paths = _paths()
        payload = {"tool_name": "Bash", "tool_input": {"command": "custom"}, "tool_response": {"stdout": "a\nb\n"}}
        feedback = adapters.claude_command_output_hook(args, paths, json.dumps(payload))
        self.assertEqual(feedback.stdout, "")
        rows = list(writer.iter_event_rows(paths.local))
        self.assertEqual(rows[0]["event_kind"], "command_output.reducer_outcome")
        self.assertEqual(rows[0]["command_family"], "unknown")
        self.assertFalse(rows[0]["had_reducer"])

    def test_claude_hook_records_small_output_before_large_output_gate(self):
        args = argparse.Namespace(config=None, large_log_lines=100, large_log_chars=None)
        paths = _paths()
        payload = {"tool_name": "Bash", "tool_input": {"command": "dotnet build"}, "tool_response": {"stdout": "ok\n", "exit_code": 0}}
        feedback = adapters.claude_command_output_hook(args, paths, json.dumps(payload))
        self.assertEqual(feedback.stdout, "")
        rows = list(writer.iter_event_rows(paths.local))
        self.assertEqual(rows[0]["command_family"], "dotnet-build")

    def test_codex_hook_replaces_large_known_success_without_claude_field(self):
        args = argparse.Namespace(config=None, large_log_lines=1, large_log_chars=None)
        payload = {
            "tool_name": "Bash",
            "tool_input": {"command": "dotnet build"},
            "tool_response": {"output": "A.cs(1,1): error CS1001: bad\nBuild FAILED.\n", "exit_code": 0},
            "session_id": "s1",
        }
        feedback = adapters.codex_command_output_hook(args, _paths(), json.dumps(payload))
        self.assertEqual(feedback.exit_code, 0)
        response = json.loads(feedback.stdout)
        self.assertFalse(response["continue"])
        self.assertIn("dotnet-build", response["stopReason"])
        self.assertEqual(response["hookSpecificOutput"]["hookEventName"], "PostToolUse")
        self.assertIn("dotnet-build", response["hookSpecificOutput"]["additionalContext"])
        self.assertNotIn("updatedToolOutput", feedback.stdout)

    def test_codex_hook_records_small_output_before_large_output_gate(self):
        args = argparse.Namespace(config=None, large_log_lines=100, large_log_chars=None)
        paths = _paths()
        payload = {"tool_name": "Bash", "tool_input": {"command": "dotnet build"}, "tool_response": {"output": "ok\n", "exit_code": 0}, "session_id": "s1"}
        feedback = adapters.codex_command_output_hook(args, paths, json.dumps(payload))
        self.assertEqual(feedback.stdout, "")
        rows = list(writer.iter_event_rows(paths.local))
        self.assertEqual(rows[0]["event_kind"], "command_output.reducer_outcome")
        self.assertEqual(rows[0]["provider"], "codex")
        self.assertEqual(rows[0]["command_family"], "dotnet-build")

    def test_codex_hook_skips_known_failure_to_avoid_retry_hook_conflict(self):
        args = argparse.Namespace(config=None, large_log_lines=1, large_log_chars=None)
        paths = _paths()
        payload = {
            "tool_name": "Bash",
            "tool_input": {"command": "dotnet build"},
            "tool_response": {"output": "A.cs(1,1): error CS1001: bad\nBuild FAILED.\n", "exit_code": 1},
            "session_id": "s1",
        }
        feedback = adapters.codex_command_output_hook(args, paths, json.dumps(payload))
        self.assertEqual(feedback.stdout, "")
        rows = list(writer.iter_event_rows(paths.local))
        self.assertEqual(rows[0]["event_kind"], "command_output.reducer_outcome")
        self.assertEqual(rows[0]["provider"], "codex")
        self.assertEqual(rows[0]["exit_code"], 1)

    def test_codex_hook_skips_failure_from_model_visible_string_output(self):
        args = argparse.Namespace(config=None, large_log_lines=1, large_log_chars=None)
        payload = {
            "tool_name": "Bash",
            "tool_input": {"command": "dotnet build"},
            "tool_response": "Process exited with code 1\nA.cs(1,1): error CS1001: bad\nBuild FAILED.\n",
            "session_id": "s1",
        }
        feedback = adapters.codex_command_output_hook(args, _paths(), json.dumps(payload))
        self.assertEqual(feedback.stdout, "")

    def test_retry_guard_is_silent_below_threshold_and_reports_at_threshold(self):
        paths = _paths()
        args = argparse.Namespace(config=None, max_attempts=2)
        payload = json.dumps({"tool_name": "Bash", "tool_input": {"command": "dotnet build"}, "error": "Exit code 1\nboom", "session_id": "s1"})
        first = adapters.claude_retry_guard_hook(args, paths, payload)
        second = adapters.claude_retry_guard_hook(args, paths, payload)
        self.assertEqual(first.stderr, "")
        self.assertEqual(second.exit_code, 2)
        self.assertIn("repeated 2 times", second.stderr)

    def test_retry_guard_skips_interrupt_and_legitimate_nonzero(self):
        args = argparse.Namespace(config=None, max_attempts=1)
        interrupt = adapters.claude_retry_guard_hook(args, _paths(), json.dumps({"tool_name": "Bash", "error": "Exit code 1", "is_interrupt": True}))
        diff = adapters.claude_retry_guard_hook(args, _paths(), json.dumps({"tool_name": "Bash", "tool_input": {"command": "git diff --quiet"}, "error": "Exit code 1"}))
        self.assertEqual(interrupt.stderr, "")
        self.assertEqual(diff.stderr, "")

    def test_retry_guard_skips_missing_session_id(self):
        args = argparse.Namespace(config=None, max_attempts=1)
        payload = json.dumps({"tool_name": "Bash", "tool_input": {"command": "dotnet build"}, "error": "Exit code 1\nboom"})
        feedback = adapters.claude_retry_guard_hook(args, _paths(), payload)
        self.assertEqual(feedback.stderr, "")

    def test_codex_retry_guard_uses_post_tool_use_output_at_threshold(self):
        paths = _paths()
        args = argparse.Namespace(config=None, max_attempts=2)
        payload = json.dumps(
            {
                "tool_name": "Bash",
                "tool_input": {"command": "dotnet build"},
                "tool_response": {"output": "Exit code 1\nA.cs(1,1): error CS1001: bad\nBuild FAILED.\n"},
                "session_id": "s1",
            }
        )
        first = adapters.codex_retry_guard_hook(args, paths, payload)
        second = adapters.codex_retry_guard_hook(args, paths, payload)
        self.assertEqual(first.stdout, "")
        self.assertEqual(second.exit_code, 0)
        response = json.loads(second.stdout)
        self.assertEqual(response["decision"], "block")
        self.assertIn("repeated 2 times", response["reason"])
        self.assertIn("PostToolUse", response["hookSpecificOutput"]["hookEventName"])

    def test_codex_retry_guard_skips_success_and_missing_session(self):
        args = argparse.Namespace(config=None, max_attempts=1)
        success = adapters.codex_retry_guard_hook(
            args,
            _paths(),
            json.dumps({"tool_name": "Bash", "tool_response": {"output": "ok", "exit_code": 0}, "session_id": "s1"}),
        )
        missing_session = adapters.codex_retry_guard_hook(
            args,
            _paths(),
            json.dumps({"tool_name": "Bash", "tool_response": {"output": "Exit code 1\nboom"}}),
        )
        self.assertEqual(success.stdout, "")
        self.assertEqual(missing_session.stdout, "")

    def test_retry_exit_code_matches_prefixed_error(self):
        self.assertEqual(adapters.retry_exit_code_from_error("Error: Exit code 2\nboom"), 2)
        self.assertEqual(adapters.retry_exit_code_from_error("Process exited with code 1\nboom"), 1)


if __name__ == "__main__":
    unittest.main()
