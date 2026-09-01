"""Provider hook adapters over the command-output reducer registry."""

from __future__ import annotations

import dataclasses
import json
import re
from pathlib import Path

from hydra_engine.agent_hooks.io import store_private_log
from hydra_engine.agent_hooks.retry_state import record_retry_failure
from hydra_engine.agent_hooks.token_budget import (
    LARGE_LOG_CHARS_DEFAULT,
    LARGE_LOG_LINES_DEFAULT,
    RETRY_MAX_ATTEMPTS_DEFAULT,
    SUMMARY_MAX_LINES_DEFAULT,
    policy_bool,
    policy_int,
    token_hook_policy,
)
from hydra_engine.command_output import hook_telemetry, rendering, shell
from hydra_engine.documents.tokens import display_path

RETRY_EXIT_CODE_RE = re.compile(r"\b(?:Exit code|Process exited with code) (-?\d+)\b")
RETRY_INTERRUPT_RE = re.compile(r"interrupted by user|doesn't want to take this action", re.IGNORECASE)
RETRY_LEGITIMATE_NONZERO_COMMANDS = frozenset({"grep", "rg", "egrep", "fgrep", "test", "["})


@dataclasses.dataclass(frozen=True)
class HookFeedback:
    exit_code: int
    stdout: str = ""
    stderr: str = ""


def display_stored_path(path: Path, root: Path) -> str:
    return display_path(path, root)


def redact_model_visible(text: str) -> str:
    return rendering.redact_obvious_secrets(text)


def bash_output_from_response(tool_response: object) -> tuple[str, int | None]:
    if isinstance(tool_response, str):
        return tool_response, retry_exit_code_from_error(tool_response)
    if not isinstance(tool_response, dict):
        return "", None
    stdout = str(tool_response.get("stdout") or "")
    stderr = str(tool_response.get("stderr") or "")
    if stdout or stderr:
        output = stdout + ("\n" + stderr if stdout and stderr else stderr)
    else:
        output = next((value for field in ("output", "text", "content") if isinstance((value := tool_response.get(field)), str)), "")
    exit_code_value = next(
        (
            value
            for field in ("exit_code", "exitCode", "return_code", "returnCode")
            if isinstance((value := tool_response.get(field)), int)
        ),
        None,
    )
    exit_code = exit_code_value if isinstance(exit_code_value, int) else None
    if exit_code is None and output:
        exit_code = retry_exit_code_from_error(output)
    return output, exit_code


def reduced_command_result_text(args, paths, text: str, raw_output_path: Path | None):
    return hook_telemetry.reduced_command_result_text(args, paths, text, raw_output_path)


def claude_command_output_hook(args, paths, raw_payload: str) -> HookFeedback:
    data = _json_object(raw_payload)
    if not data or data.get("tool_name") != "Bash":
        return HookFeedback(0)
    tool_input = data.get("tool_input")
    command = str(tool_input.get("command") or "") if isinstance(tool_input, dict) else ""
    output, exit_code = bash_output_from_response(data.get("tool_response"))
    if not output:
        return HookFeedback(0)

    policy = token_hook_policy(args.config, paths.local, paths.root / ".hydra-framework")
    reduction = hook_telemetry.record_claude_capture(args, paths, data, command, output, exit_code)
    if not _is_large_output(args, paths, output):
        return HookFeedback(0)
    raw_output_path = store_private_log(paths, output, command or "command-result") if policy_bool(policy, "store_full_logs", False) else None
    if not reduction.has_reducer:
        return HookFeedback(0)
    raw_display = display_path(raw_output_path, paths.root) if raw_output_path is not None else ""
    replacement = rendering.render_reduction(reduction, raw_output_path=raw_display, failed=False)
    return HookFeedback(0, stdout=json.dumps({"hookSpecificOutput": {"hookEventName": "PostToolUse", "updatedToolOutput": replacement}}))


def codex_command_output_hook(args, paths, raw_payload: str) -> HookFeedback:
    data = _json_object(raw_payload)
    if not data or data.get("tool_name") != "Bash":
        return HookFeedback(0)
    tool_input = data.get("tool_input")
    command = str(tool_input.get("command") or "") if isinstance(tool_input, dict) else ""
    output, exit_code = bash_output_from_response(data.get("tool_response"))
    if not output:
        return HookFeedback(0)

    reduction = hook_telemetry.record_provider_capture(args, paths, "codex", data, command, output, exit_code)
    if exit_code not in {None, 0} or not _is_large_output(args, paths, output):
        return HookFeedback(0)

    policy = token_hook_policy(args.config, paths.local, paths.root / ".hydra-framework")
    raw_output_path = store_private_log(paths, output, command or "command-result") if policy_bool(policy, "store_full_logs", False) else None
    if not reduction.has_reducer:
        return HookFeedback(0)
    raw_display = display_path(raw_output_path, paths.root) if raw_output_path is not None else ""
    replacement = rendering.render_reduction(reduction, raw_output_path=raw_display, failed=False)
    return HookFeedback(
        0,
        stdout=json.dumps(
            {
                "continue": False,
                "stopReason": replacement,
                "hookSpecificOutput": {"hookEventName": "PostToolUse", "additionalContext": replacement},
            }
        ),
    )


def claude_retry_guard_hook(args, paths, raw_payload: str) -> HookFeedback:
    data = _json_object(raw_payload)
    if not data or data.get("tool_name") != "Bash":
        return HookFeedback(0)
    text = data.get("error")
    if not isinstance(text, str) or not text.strip():
        return HookFeedback(0)
    if data.get("is_interrupt") or RETRY_INTERRUPT_RE.search(text):
        return HookFeedback(0)
    tool_input = data.get("tool_input")
    command = str(tool_input.get("command") or "") if isinstance(tool_input, dict) else ""
    if retry_command_is_legitimate_nonzero(command):
        return HookFeedback(0)

    policy = token_hook_policy(args.config, paths.local, paths.root / ".hydra-framework")
    max_attempts = args.max_attempts if args.max_attempts is not None else policy_int(policy, "retry_max_attempts", RETRY_MAX_ATTEMPTS_DEFAULT)
    key = str(data.get("session_id") or "")
    if not key:
        return HookFeedback(0)
    exit_code = retry_exit_code_from_error(text)
    try:
        fingerprint, record = record_retry_failure(paths, command, exit_code, text, key)
    except OSError as error:
        return HookFeedback(0, stderr=f"Hydra retry guard: could not record failure state: {error}")

    count = int(record["count"])
    if count < max_attempts:
        return HookFeedback(0)
    lines = [f"Hydra retry guard: this failure has now repeated {count} times in this session."]
    if command:
        lines.append(f"Command: {rendering.redact_obvious_secrets(command)}")
    if exit_code is not None:
        lines.append(f"Exit code: {exit_code}")
    lines.append(f"Fingerprint: {fingerprint[:12]} (identical error text, not merely the same command).")
    lines.append("Stop normal retries. Summarize verified evidence, name the unverified assumption, then change hypothesis or ask the owner.")
    return HookFeedback(2, stderr="\n".join(lines))


def codex_retry_guard_hook(args, paths, raw_payload: str) -> HookFeedback:
    data = _json_object(raw_payload)
    if not data or data.get("tool_name") != "Bash":
        return HookFeedback(0)
    output, exit_code = bash_output_from_response(data.get("tool_response"))
    if not output or exit_code in {None, 0}:
        return HookFeedback(0)
    tool_input = data.get("tool_input")
    command = str(tool_input.get("command") or "") if isinstance(tool_input, dict) else ""
    if retry_command_is_legitimate_nonzero(command):
        return HookFeedback(0)

    policy = token_hook_policy(args.config, paths.local, paths.root / ".hydra-framework")
    max_attempts = args.max_attempts if args.max_attempts is not None else policy_int(policy, "retry_max_attempts", RETRY_MAX_ATTEMPTS_DEFAULT)
    key = str(data.get("session_id") or "")
    if not key:
        return HookFeedback(0)
    try:
        fingerprint, record = record_retry_failure(paths, command, exit_code, output, key)
    except OSError as error:
        return HookFeedback(0, stderr=f"Hydra Codex retry guard: could not record failure state: {error}")

    count = int(record["count"])
    if count < max_attempts:
        return HookFeedback(0)
    lines = [f"Hydra retry guard: this Codex Bash failure has now repeated {count} times in this session."]
    if command:
        lines.append(f"Command: {rendering.redact_obvious_secrets(command)}")
    lines.append(f"Exit code: {exit_code}")
    lines.append(f"Fingerprint: {fingerprint[:12]} (identical command output, not merely the same command).")
    lines.append("Stop normal retries. Summarize verified evidence, name the unverified assumption, then change hypothesis or ask the owner.")
    feedback = "\n".join(lines)
    return HookFeedback(
        0,
        stdout=json.dumps(
            {
                "decision": "block",
                "reason": feedback,
                "hookSpecificOutput": {"hookEventName": "PostToolUse", "additionalContext": feedback},
            }
        ),
    )


def retry_exit_code_from_error(text: str) -> int | None:
    match = RETRY_EXIT_CODE_RE.search(text)
    return int(match.group(1)) if match else None


def retry_command_is_legitimate_nonzero(command: str) -> bool:
    segments = shell.split_top_level_segments(command.replace("\n", ";"))
    tokens = shell.strip_env_prefix(segments[-1]) if segments else ()
    if not tokens:
        return False
    name = Path(tokens[0]).name
    if name in RETRY_LEGITIMATE_NONZERO_COMMANDS:
        return True
    if name != "git" or shell.git_subcommand(tokens) != "diff":
        return False
    return any(token in {"--quiet", "--exit-code"} for token in tokens)


def _json_object(raw_payload: str) -> dict:
    if not raw_payload:
        return {}
    try:
        data = json.loads(raw_payload)
    except json.JSONDecodeError:
        return {}
    return data if isinstance(data, dict) else {}


def _is_large_output(args, paths, output: str) -> bool:
    policy = token_hook_policy(args.config, paths.local, paths.root / ".hydra-framework")
    lines = output.splitlines()
    large_log_lines = args.large_log_lines if getattr(args, "large_log_lines", None) is not None else policy_int(policy, "large_log_lines", LARGE_LOG_LINES_DEFAULT)
    large_log_chars = args.large_log_chars if getattr(args, "large_log_chars", None) is not None else policy_int(policy, "large_log_chars", LARGE_LOG_CHARS_DEFAULT)
    return len(lines) > large_log_lines or len(output) > large_log_chars
