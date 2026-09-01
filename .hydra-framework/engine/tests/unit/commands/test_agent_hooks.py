"""Mirror test for `hydra_engine.commands.agent_hooks`."""

from __future__ import annotations

import argparse
import contextlib
import io as stdlib_io
import json
import sys
import tempfile
import unittest
from unittest import mock
from pathlib import Path

_SRC = Path(__file__).resolve().parents[3] / "src"
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

from hydra_engine import thresholds  # noqa: E402
from hydra_engine.agent_hooks.paths import AgentHooksPaths  # noqa: E402
from hydra_engine.cli.dispatch import RepoContext  # noqa: E402
from hydra_engine.commands import agent_hooks  # noqa: E402


def _paths() -> AgentHooksPaths:
    root = Path(tempfile.mkdtemp(prefix="commands-agent-hooks-"))
    return AgentHooksPaths(root=root, local=root / ".hydra-framework.local")


def _ctx(**overrides: int) -> RepoContext:
    root = Path(tempfile.mkdtemp(prefix="commands-agent-hooks-ctx-"))
    config = root / ".hydra-framework/config"
    config.mkdir(parents=True)
    lines = ["schema: hydra-framework.engine-policy.v1", "thresholds:"]
    for entry in thresholds.THRESHOLDS:
        if entry.classification == thresholds.TEAM_TUNABLE_POLICY:
            lines.append(f"  {entry.key}: {overrides.get(entry.key, entry.value)}")
    (config / "engine-policy.yaml").write_text("\n".join(lines) + "\n", encoding="utf-8")
    (config / "delegation-policy.yaml").write_text(
        "schema: hydra-framework.delegation-policy.v1\n"
        "enabled: true\nmax_active_workers: 2\nmax_depth: 1\n"
        "allowed_reasons:\n  - inspection\n"
        "role_defaults:\n  allowed_capability_classes:\n    - fast-default\n"
        "  fallback_capability_class: fast-default\n  effort_ceiling: max\n"
        "roles: {}\n",
        encoding="utf-8",
    )
    return RepoContext.for_root(root)


class CommandSummarizeLogTests(unittest.TestCase):
    def test_reports_line_count_and_excerpt(self):
        log_path = _paths().local.parent / "input.log"
        log_path.parent.mkdir(parents=True, exist_ok=True)
        log_path.write_text("hello\nworld\n", encoding="utf-8")
        args = argparse.Namespace(file=str(log_path), store_full=False, name=None, command=None, exit_code=None, max_lines=10)
        out = stdlib_io.StringIO()
        with contextlib.redirect_stdout(out):
            result = agent_hooks.command_summarize_log(args, _paths())
        self.assertEqual(result.exit_code, 0)
        self.assertIn("Input lines: 2", out.getvalue())

    def test_store_full_writes_private_log_and_reports_it(self):
        paths = _paths()
        log_path = paths.root / "input.log"
        log_path.write_text("boom\n", encoding="utf-8")
        args = argparse.Namespace(file=str(log_path), store_full=True, name="mine", command=None, exit_code=None, max_lines=10)
        out = stdlib_io.StringIO()
        with contextlib.redirect_stdout(out):
            result = agent_hooks.command_summarize_log(args, paths)
        self.assertEqual(result.exit_code, 0)
        self.assertIn("Stored full log privately:", out.getvalue())
        self.assertTrue(any(paths.local.joinpath("logs").glob("*mine.log")))

    def test_dispatch_uses_configured_summary_lines_when_cli_omits_value(self):
        ctx = _ctx(**{"hydra_engine.agent_hooks.token_budget.SUMMARY_MAX_LINES_DEFAULT": 1})
        log_path = ctx.root / "input.log"
        log_path.write_text("first\nsecond\nthird\n", encoding="utf-8")
        args = argparse.Namespace(file=str(log_path), store_full=False, name=None, command=None, exit_code=None, max_lines=None)
        out = stdlib_io.StringIO()
        with contextlib.redirect_stdout(out):
            self.assertEqual(agent_hooks._dispatch_summarize_log(args, ctx), 0)
        self.assertEqual(args.max_lines, 1)
        self.assertIn("... omitted 2 lines", out.getvalue())


class CommandRetryGuardTests(unittest.TestCase):
    def test_success_records_nothing(self):
        args = argparse.Namespace(exit_code=0, file=None, command="x", key=None, reset=False, max_attempts=2)
        out = stdlib_io.StringIO()
        with contextlib.redirect_stdout(out):
            result = agent_hooks.command_retry_guard(args, _paths())
        self.assertEqual(result.exit_code, 0)
        self.assertIn("no failure recorded", out.getvalue())

    def test_repeated_failure_halts_at_threshold(self):
        paths = _paths()
        args = argparse.Namespace(exit_code=1, file=None, command="x", key="k", reset=False, max_attempts=1)
        out = stdlib_io.StringIO()
        with contextlib.redirect_stdout(out):
            result = agent_hooks.command_retry_guard(args, paths)
        self.assertEqual(result.exit_code, 2)
        self.assertIn("Repeated failure threshold reached", out.getvalue())

    def test_dispatch_uses_configured_retry_attempts_when_cli_omits_value(self):
        ctx = _ctx(**{"hydra_engine.agent_hooks.token_budget.RETRY_MAX_ATTEMPTS_DEFAULT": 1})
        args = argparse.Namespace(exit_code=1, file=None, command="x", key="k", reset=False, max_attempts=None)
        out = stdlib_io.StringIO()
        with contextlib.redirect_stdout(out):
            exit_code = agent_hooks._dispatch_retry_guard(args, ctx)
        self.assertEqual(exit_code, 2)
        self.assertIn("Repeated failure threshold reached", out.getvalue())


class CommandHookTokenPreContextTests(unittest.TestCase):
    def test_no_budget_configured_reports_estimate(self):
        args = argparse.Namespace(require_budget=False, report=True)
        out = stdlib_io.StringIO()
        with contextlib.redirect_stdout(out):
            result = agent_hooks.command_hook_token_pre_context(args, 500, None, [])
        self.assertEqual(result.exit_code, 0)
        self.assertIn("500 approx tokens", out.getvalue())

    def test_budget_exceeded_lists_top_rows_on_stderr(self):
        args = argparse.Namespace(require_budget=False, report=False)
        rows = [{"approx_tokens": 900, "path": "big.md"}, {"approx_tokens": 10, "path": "small.md"}]
        err = stdlib_io.StringIO()
        with contextlib.redirect_stderr(err):
            result = agent_hooks.command_hook_token_pre_context(args, 910, 100, rows)
        self.assertEqual(result.exit_code, 2)
        self.assertIn("big.md", err.getvalue())


class CommandHookTokenCommandResultTests(unittest.TestCase):
    def test_small_successful_output_is_a_no_op(self):
        args = argparse.Namespace(
            config=None, file=None, large_log_lines=None, large_log_chars=None, max_lines=None,
            max_attempts=None, store_full=False, exit_code=0, command="x", name=None, key=None,
        )
        out = stdlib_io.StringIO()
        with contextlib.redirect_stdout(out):
            result = agent_hooks.command_hook_token_command_result(args, _paths())
        self.assertEqual(result.exit_code, 0)
        self.assertEqual(out.getvalue(), "")

    def test_failed_command_reports_and_records_fingerprint(self):
        args = argparse.Namespace(
            config=None, file=None, large_log_lines=None, large_log_chars=None, max_lines=None,
            max_attempts=None, store_full=False, exit_code=1, command="x", name=None, key=None,
        )
        out = stdlib_io.StringIO()
        with contextlib.redirect_stdout(out):
            result = agent_hooks.command_hook_token_command_result(args, _paths())
        self.assertEqual(result.exit_code, 0)
        self.assertIn("command failed", out.getvalue())
        self.assertIn("Retry fingerprint", out.getvalue())

    def test_failed_command_redacts_command_preface(self):
        args = argparse.Namespace(
            config=None, file=None, large_log_lines=None, large_log_chars=None, max_lines=None,
            max_attempts=None, store_full=False, exit_code=1, command="curl --api-key 'secret two'", name=None, key=None,
        )
        out = stdlib_io.StringIO()
        with contextlib.redirect_stdout(out):
            result = agent_hooks.command_hook_token_command_result(args, _paths())
        self.assertEqual(result.exit_code, 0)
        self.assertNotIn("secret two", out.getvalue())


class CommandHookCommandOutputTests(unittest.TestCase):
    def test_large_known_bash_success_prints_claude_replacement_payload(self):
        args = argparse.Namespace(config=None, large_log_lines=1, large_log_chars=None)
        payload = json.dumps(
            {
                "tool_name": "Bash",
                "tool_input": {"command": "dotnet build"},
                "tool_response": {"stdout": "A.cs(1,1): error CS1001: bad\nBuild FAILED.\n"},
            }
        )
        out = stdlib_io.StringIO()
        stdin = stdlib_io.StringIO(payload)
        with contextlib.redirect_stdout(out), mock.patch("sys.stdin", stdin):
            result = agent_hooks.command_hook_command_output(args, _paths())
        self.assertEqual(result.exit_code, 0)
        self.assertIn("updatedToolOutput", out.getvalue())

    def test_large_known_bash_success_prints_codex_replacement_payload(self):
        args = argparse.Namespace(config=None, large_log_lines=1, large_log_chars=None)
        payload = json.dumps(
            {
                "tool_name": "Bash",
                "tool_input": {"command": "dotnet build"},
                "tool_response": {"output": "A.cs(1,1): error CS1001: bad\nBuild FAILED.\n", "exit_code": 0},
                "session_id": "s1",
            }
        )
        out = stdlib_io.StringIO()
        stdin = stdlib_io.StringIO(payload)
        with contextlib.redirect_stdout(out), mock.patch("sys.stdin", stdin):
            result = agent_hooks.command_hook_codex_command_output(args, _paths())
        self.assertEqual(result.exit_code, 0)
        response = json.loads(out.getvalue())
        self.assertFalse(response["continue"])
        self.assertIn("dotnet-build", response["stopReason"])
        self.assertNotIn("updatedToolOutput", out.getvalue())


class CommandHookRetryGuardTests(unittest.TestCase):
    def test_failure_hook_is_silent_below_threshold(self):
        args = argparse.Namespace(config=None, max_attempts=2)
        payload = json.dumps({"tool_name": "Bash", "tool_input": {"command": "dotnet build"}, "error": "Exit code 1\nboom", "session_id": "s1"})
        err = stdlib_io.StringIO()
        with contextlib.redirect_stderr(err), mock.patch("sys.stdin", stdlib_io.StringIO(payload)):
            result = agent_hooks.command_hook_retry_guard(args, _paths())
        self.assertEqual(result.exit_code, 0)
        self.assertEqual(err.getvalue(), "")

    def test_codex_retry_hook_prints_block_payload_at_threshold(self):
        args = argparse.Namespace(config=None, max_attempts=1)
        payload = json.dumps(
            {
                "tool_name": "Bash",
                "tool_input": {"command": "dotnet build"},
                "tool_response": {"output": "Exit code 1\nA.cs(1,1): error CS1001: bad\nBuild FAILED.\n"},
                "session_id": "s1",
            }
        )
        out = stdlib_io.StringIO()
        with contextlib.redirect_stdout(out), mock.patch("sys.stdin", stdlib_io.StringIO(payload)):
            result = agent_hooks.command_hook_codex_retry_guard(args, _paths())
        self.assertEqual(result.exit_code, 0)
        response = json.loads(out.getvalue())
        self.assertEqual(response["decision"], "block")
        self.assertIn("Codex Bash failure", response["reason"])


if __name__ == "__main__":
    unittest.main()
