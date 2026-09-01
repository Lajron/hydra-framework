"""agent_hooks command decisions.

`command_hook_token_pre_context` takes its context measurement (`total`,
`rows`) as plain data rather than calling `measure_context_surfaces` itself:
that function belongs to the not-yet-moved `knowledge`/`surfaces` cluster,
and this module must not import `scripts/hydra.py` to
reach it. `command_hook_post_edit` is not here at all -- see
`hydra_engine.agent_hooks`'s docstring.
"""

from __future__ import annotations

import sys

from hydra_engine.command_output import adapters as command_output_adapters
from hydra_engine.agent_hooks.io import read_stdin_or_file, store_private_log
from hydra_engine.agent_hooks.logs import summarize_log_text
from hydra_engine.agent_hooks.paths import AgentHooksPaths
from hydra_engine.agent_hooks.retry_state import record_retry_failure, reset_retry_failure
from hydra_engine.agent_hooks.token_budget import (
    LARGE_LOG_CHARS_DEFAULT,
    LARGE_LOG_LINES_DEFAULT,
    RETRY_MAX_ATTEMPTS_DEFAULT,
    SUMMARY_MAX_LINES_DEFAULT,
    configured_context_budget,
    policy_bool,
    policy_int,
    token_hook_policy,
)
from hydra_engine.commands import CommandResult
from hydra_engine.knowledge.surfaces import measure_context_surfaces

RETRY_FINGERPRINT_DISPLAY_CHARS = 12
TOKEN_BUDGET_EXCEEDED_REPORT_LIMIT = 5


def command_summarize_log(args, paths: AgentHooksPaths) -> CommandResult:
    text = read_stdin_or_file(args.file)
    if args.store_full and text:
        target = store_private_log(paths, text, args.name or args.command or "log")
        print(f"Stored full log privately: {command_output_adapters.display_stored_path(target, paths.root)}")

    print("Hydra log summary")
    if args.command:
        print(f"Command: {args.command}")
    if args.exit_code is not None:
        print(f"Exit code: {args.exit_code}")
    print(f"Input lines: {len(text.splitlines())}")
    print("Relevant excerpt:")
    excerpt = summarize_log_text(text, args.max_lines)
    if excerpt:
        for line in excerpt:
            print(line)
    else:
        print("<empty log>")
    return CommandResult(0)


def command_retry_guard(args, paths: AgentHooksPaths) -> CommandResult:
    if args.exit_code == 0:
        print("Hydra retry guard: command succeeded; no failure recorded")
        return CommandResult(0)

    text = read_stdin_or_file(args.file)
    command = args.command or ""
    key = args.key or "default"

    if args.reset:
        if reset_retry_failure(paths, command, args.exit_code, text, key):
            print("Hydra retry guard: reset matching failure fingerprint")
        else:
            print("Hydra retry guard: no matching failure fingerprint to reset")
        return CommandResult(0)

    fingerprint, record = record_retry_failure(paths, command, args.exit_code, text, key)
    count = int(record["count"])
    print(f"Hydra retry guard: failure fingerprint {fingerprint[:RETRY_FINGERPRINT_DISPLAY_CHARS]} attempt {count}/{args.max_attempts}")
    if count >= args.max_attempts:
        print("Repeated failure threshold reached. Summarize verified evidence, change hypothesis, narrow validation, or ask a human.")
        return CommandResult(2)
    return CommandResult(0)


def command_hook_token_pre_context(args, total: int, budget: int | None, rows: list[dict]) -> CommandResult:
    if budget is None:
        if args.require_budget:
            print(
                "Hydra token hook: no context budget configured. Set --budget or a private monitoring policy file.",
                file=sys.stderr,
            )
            return CommandResult(2)
        if args.report:
            print(f"Hydra token hook: no context budget configured; current estimate is {total} approx tokens")
        return CommandResult(0)

    if total > budget:
        print(f"Hydra token hook: context budget exceeded: {total} > {budget} approx tokens", file=sys.stderr)
        for row in sorted(rows, key=lambda item: int(item["approx_tokens"]), reverse=True)[:TOKEN_BUDGET_EXCEEDED_REPORT_LIMIT]:
            print(f"- {row['approx_tokens']} approx tokens: {row['path']}", file=sys.stderr)
        return CommandResult(2)

    if args.report:
        print(f"Hydra token hook: context estimate {total}/{budget} approx tokens")
    return CommandResult(0)


def command_hook_token_command_result(args, paths: AgentHooksPaths) -> CommandResult:
    policy = token_hook_policy(args.config, paths.local, paths.root / ".hydra-framework")
    text = read_stdin_or_file(args.file)
    lines = text.splitlines()
    large_log_lines = args.large_log_lines if args.large_log_lines is not None else policy_int(policy, "large_log_lines", LARGE_LOG_LINES_DEFAULT)
    large_log_chars = args.large_log_chars if args.large_log_chars is not None else policy_int(policy, "large_log_chars", LARGE_LOG_CHARS_DEFAULT)
    max_attempts = args.max_attempts if args.max_attempts is not None else policy_int(policy, "retry_max_attempts", RETRY_MAX_ATTEMPTS_DEFAULT)
    store_full = args.store_full or policy_bool(policy, "store_full_logs", False)
    failed = args.exit_code is not None and args.exit_code != 0
    large = len(lines) > large_log_lines or len(text) > large_log_chars

    if not failed and not large:
        return CommandResult(0)

    stored = None
    if store_full and text:
        stored = store_private_log(paths, text, args.name or args.command or "command-result")

    halt = False
    if failed:
        fingerprint, record = record_retry_failure(paths, args.command or "", args.exit_code, text, args.key or "default")
        count = int(record["count"])
        halt = count >= max_attempts
        print("Hydra command hook: command failed")
        if args.command:
            print(f"Command: {command_output_adapters.redact_model_visible(args.command)}")
        print(f"Exit code: {args.exit_code}")
        print(f"Retry fingerprint: {fingerprint[:RETRY_FINGERPRINT_DISPLAY_CHARS]} attempt {count}/{max_attempts}")
        if halt:
            print("Repeated failure threshold reached. Change hypothesis, narrow validation, or ask a human before retrying.")
    else:
        print("Hydra command hook: large command output summarized")
        if args.command:
            print(f"Command: {command_output_adapters.redact_model_visible(args.command)}")

    _reduction, summary = command_output_adapters.reduced_command_result_text(args, paths, text, stored)
    print(summary)
    return CommandResult(2 if halt else 0)


def command_hook_command_output(args, paths: AgentHooksPaths) -> CommandResult:
    feedback = command_output_adapters.claude_command_output_hook(args, paths, sys.stdin.read())
    if feedback.stdout:
        print(feedback.stdout)
    if feedback.stderr:
        print(feedback.stderr, file=sys.stderr)
    return CommandResult(feedback.exit_code)


def command_hook_codex_command_output(args, paths: AgentHooksPaths) -> CommandResult:
    feedback = command_output_adapters.codex_command_output_hook(args, paths, sys.stdin.read())
    if feedback.stdout:
        print(feedback.stdout)
    if feedback.stderr:
        print(feedback.stderr, file=sys.stderr)
    return CommandResult(feedback.exit_code)


def command_hook_retry_guard(args, paths: AgentHooksPaths) -> CommandResult:
    feedback = command_output_adapters.claude_retry_guard_hook(args, paths, sys.stdin.read())
    if feedback.stdout:
        print(feedback.stdout)
    if feedback.stderr:
        print(feedback.stderr, file=sys.stderr)
    return CommandResult(feedback.exit_code)


def command_hook_codex_retry_guard(args, paths: AgentHooksPaths) -> CommandResult:
    feedback = command_output_adapters.codex_retry_guard_hook(args, paths, sys.stdin.read())
    if feedback.stdout:
        print(feedback.stdout)
    if feedback.stderr:
        print(feedback.stderr, file=sys.stderr)
    return CommandResult(feedback.exit_code)


def register(subparsers) -> None:
    """Add `summarize-log`, `retry-guard`, and `hook-token`."""
    log = subparsers.add_parser("summarize-log", help="Reduce noisy command output before it enters model context")
    log.add_argument("--file", help="Read log text from a file instead of stdin")
    log.add_argument("--command", default="", help="Command that produced the log")
    log.add_argument("--exit-code", type=int, help="Exit code from the command")
    log.add_argument("--max-lines", type=int, help="Maximum excerpt lines to print")
    log.add_argument("--store-full", action="store_true", help="Store the full input log under .hydra-framework.local/logs/")
    log.add_argument("--name", default="", help="Private stored-log filename hint")
    log.set_defaults(func=_dispatch_summarize_log)

    retry = subparsers.add_parser("retry-guard", help="Track repeated failure fingerprints and halt normal retry loops")
    retry.add_argument("--file", help="Read failure text from a file instead of stdin")
    retry.add_argument("--command", default="", help="Command or operation that failed")
    retry.add_argument("--exit-code", type=int, help="Exit code from the command")
    retry.add_argument("--key", default="default", help="Namespace for the failure fingerprint")
    retry.add_argument("--max-attempts", type=int, help="Attempt count that triggers a halt")
    retry.add_argument("--reset", action="store_true", help="Reset the matching failure fingerprint")
    retry.set_defaults(func=_dispatch_retry_guard)

    command_output = subparsers.add_parser("hook-command-output", help="Claude Bash PostToolUse command-output reducer")
    command_output.add_argument("--config", help="Policy JSON path; defaults to the private monitoring policy file")
    command_output.add_argument("--large-log-lines", type=int, help="Line count that triggers reduction on success")
    command_output.add_argument("--large-log-chars", type=int, help="Character count that triggers reduction on success")
    command_output.set_defaults(func=_dispatch_hook_command_output)

    codex_command_output = subparsers.add_parser("hook-codex-command-output", help="Codex Bash PostToolUse command-output reducer")
    codex_command_output.add_argument("--config", help="Policy JSON path; defaults to the private monitoring policy file")
    codex_command_output.add_argument("--large-log-lines", type=int, help="Line count that triggers reduction on success")
    codex_command_output.add_argument("--large-log-chars", type=int, help="Character count that triggers reduction on success")
    codex_command_output.set_defaults(func=_dispatch_hook_codex_command_output)

    retry_hook = subparsers.add_parser("hook-retry-guard", help="Claude Bash PostToolUseFailure retry guard")
    retry_hook.add_argument("--config", help="Policy JSON path; defaults to the private monitoring policy file")
    retry_hook.add_argument("--max-attempts", type=int, help="Attempt count that triggers feedback")
    retry_hook.set_defaults(func=_dispatch_hook_retry_guard)

    codex_retry_hook = subparsers.add_parser("hook-codex-retry-guard", help="Codex Bash PostToolUse retry guard")
    codex_retry_hook.add_argument("--config", help="Policy JSON path; defaults to the private monitoring policy file")
    codex_retry_hook.add_argument("--max-attempts", type=int, help="Attempt count that triggers feedback")
    codex_retry_hook.set_defaults(func=_dispatch_hook_codex_retry_guard)

    token_hook = subparsers.add_parser("hook-token", help="Run quiet deterministic token-efficiency hook modes")
    token_hook_sub = token_hook.add_subparsers(dest="token_hook_command", required=True)

    pre_context = token_hook_sub.add_parser("pre-context", help="Check context budget silently unless it fails")
    pre_context.add_argument("--config", help="Policy JSON path; defaults to the private monitoring policy file")
    pre_context.add_argument("--budget", type=int, help="Approx-token budget for this workflow")
    pre_context.add_argument("--path", action="append", default=[], help="Additional file or directory to include")
    pre_context.add_argument("--include-generated-skills", action="store_true", help="Include generated provider skill wrapper bodies")
    pre_context.add_argument("--require-budget", action="store_true", help="Fail when no budget is configured")
    pre_context.add_argument("--report", action="store_true", help="Print a compact success or no-budget report")
    pre_context.set_defaults(func=_dispatch_hook_token_pre_context)

    command_result = token_hook_sub.add_parser("command-result", help="Summarize large/failing output and guard repeated failures")
    command_result.add_argument("--config", help="Policy JSON path; defaults to the private monitoring policy file")
    command_result.add_argument("--file", help="Read command output from a file instead of stdin")
    command_result.add_argument("--command", default="", help="Command or operation that produced the output")
    command_result.add_argument("--exit-code", type=int, help="Exit code from the command")
    command_result.add_argument("--key", default="default", help="Namespace for the retry fingerprint")
    command_result.add_argument("--large-log-lines", type=int, help="Line count that triggers summarization on success")
    command_result.add_argument("--large-log-chars", type=int, help="Character count that triggers summarization on success")
    command_result.add_argument("--max-lines", type=int, help="Maximum excerpt lines to print")
    command_result.add_argument("--max-attempts", type=int, help="Attempt count that triggers a halt")
    command_result.add_argument("--store-full", action="store_true", help="Store the full input log under .hydra-framework.local/logs/")
    command_result.add_argument("--name", default="", help="Private stored-log filename hint")
    command_result.set_defaults(func=_dispatch_hook_token_command_result)


def _dispatch_summarize_log(args, ctx) -> int:
    if args.max_lines is None:
        args.max_lines = ctx.threshold_value("hydra_engine.agent_hooks.token_budget.SUMMARY_MAX_LINES_DEFAULT")
    return command_summarize_log(args, ctx.agent_hooks_paths()).exit_code


def _dispatch_retry_guard(args, ctx) -> int:
    if args.max_attempts is None:
        args.max_attempts = ctx.threshold_value("hydra_engine.agent_hooks.token_budget.RETRY_MAX_ATTEMPTS_DEFAULT")
    return command_retry_guard(args, ctx.agent_hooks_paths()).exit_code


def _dispatch_hook_command_output(args, ctx) -> int:
    return command_hook_command_output(args, ctx.agent_hooks_paths()).exit_code


def _dispatch_hook_codex_command_output(args, ctx) -> int:
    return command_hook_codex_command_output(args, ctx.agent_hooks_paths()).exit_code


def _dispatch_hook_retry_guard(args, ctx) -> int:
    return command_hook_retry_guard(args, ctx.agent_hooks_paths()).exit_code


def _dispatch_hook_codex_retry_guard(args, ctx) -> int:
    return command_hook_codex_retry_guard(args, ctx.agent_hooks_paths()).exit_code


def _dispatch_hook_token_pre_context(args, ctx) -> int:
    paths = ctx.agent_hooks_paths()
    policy = token_hook_policy(args.config, paths.local, ctx.hydra)
    include_generated = args.include_generated_skills or policy_bool(policy, "include_generated_skills", False)
    rows, totals = measure_context_surfaces(
        ctx.context_compiler_paths(),
        include_generated,
        args.path,
        ctx.threshold_value("hydra_engine.knowledge.candidates.APPROX_CHARS_PER_TOKEN"),
    )
    budget = configured_context_budget(policy, args.budget)
    return command_hook_token_pre_context(args, totals["approx_tokens"], budget, rows).exit_code


def _dispatch_hook_token_command_result(args, ctx) -> int:
    return command_hook_token_command_result(args, ctx.agent_hooks_paths()).exit_code
