"""Telemetry-aware command-output reduction helpers for hooks."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from hydra_engine.agent_hooks.token_budget import SUMMARY_MAX_LINES_DEFAULT, policy_int, token_hook_policy
from hydra_engine.command_output import registry, rendering, telemetry
from hydra_engine.command_output.model import CommandOutput, Reduction
from hydra_engine.documents.tokens import display_path


def reduced_command_result_text(args, paths, text: str, raw_output_path: Path | None) -> tuple[Reduction, str]:
    max_lines = _summary_max_lines(args, paths)
    reduction = registry.reduce_command_output(
        CommandOutput(
            provider=getattr(args, "provider", "") or "manual",
            tool_name=getattr(args, "tool_name", "") or "",
            command=args.command or "",
            cwd=getattr(args, "cwd", "") or display_path(paths.root, paths.root),
            exit_code=args.exit_code,
            output=text,
            session_id=getattr(args, "session_id", "") or "",
            key=args.key or "default",
            raw_output_path=raw_output_path,
        ),
        max_lines,
    )
    raw_display = display_path(raw_output_path, paths.root) if raw_output_path is not None else ""
    failed = args.exit_code is not None and args.exit_code != 0
    return reduction, rendering.render_reduction(reduction, raw_output_path=raw_display, include_status=not failed)


def record_claude_capture(args, paths, data: dict[str, Any], command: str, output: str, exit_code: int | None) -> Reduction:
    return record_provider_capture(args, paths, "claude", data, command, output, exit_code)


def record_provider_capture(args, paths, provider: str, data: dict[str, Any], command: str, output: str, exit_code: int | None) -> Reduction:
    telemetry.capture_session_aggregate(paths.local, provider, data)
    reduction = reduce_provider_command(args, paths, provider, data, command, output, exit_code)
    telemetry.record_reducer_event(paths.local, reduction)
    return reduction


def reduce_provider_command(args, paths, provider: str, data: dict[str, Any], command: str, output: str, exit_code: int | None) -> Reduction:
    session_id = str(data.get("session_id") or "")
    return registry.reduce_command_output(
        CommandOutput(
            provider=provider,
            tool_name="Bash",
            command=command,
            cwd=str(data.get("cwd") or "") or display_path(paths.root, paths.root),
            exit_code=exit_code,
            output=output,
            session_id=session_id,
            key=session_id or "default",
            raw_output_path=None,
        ),
        _summary_max_lines(args, paths),
    )


def _summary_max_lines(args, paths) -> int:
    policy = token_hook_policy(args.config, paths.local, paths.root / ".hydra-framework")
    return args.max_lines if getattr(args, "max_lines", None) is not None else policy_int(policy, "summary_max_lines", SUMMARY_MAX_LINES_DEFAULT)
