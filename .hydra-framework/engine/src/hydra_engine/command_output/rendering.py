"""Render reviewed command-output reductions."""

from __future__ import annotations

from hydra_engine.command_output.model import CommandOutput, Reduction
from hydra_engine.command_output.reducers import selection

REDUCER_SCHEMA = selection.REDUCER_SCHEMA
REDUCER_VERSION = selection.REDUCER_VERSION
redact_obvious_secrets = selection.redact_obvious_secrets


def reduce_with_family(command_output: CommandOutput, family: str, reducer_name: str, max_lines: int) -> Reduction:
    return Reduction(**selection.reduction_fields(command_output, family, reducer_name, max_lines))


def unknown_reduction(command_output: CommandOutput) -> Reduction:
    status = "failed" if command_output.exit_code not in {None, 0} else "completed"
    return Reduction(
        schema=REDUCER_SCHEMA,
        provider=command_output.provider or "manual",
        tool_name=command_output.tool_name,
        command=redact_obvious_secrets(command_output.command),
        cwd=command_output.cwd,
        exit_code=command_output.exit_code,
        family="unknown",
        reducer_name="none",
        reducer_version=REDUCER_VERSION,
        compact_summary=f"unknown command {status}; raw output omitted because no reviewed reducer matched",
        important_lines=(),
        omitted_lines=command_output.line_count,
        omitted_chars=command_output.char_count,
        input_line_count=command_output.line_count,
        input_char_count=command_output.char_count,
        session_id=command_output.session_id,
        key=command_output.key,
    )


def render_reduction(
    reduction: Reduction,
    *,
    raw_output_path: str = "",
    failed: bool | None = None,
    include_status: bool = True,
) -> str:
    is_failed = reduction.exit_code is not None and reduction.exit_code != 0 if failed is None else failed
    lines: list[str] = []
    if include_status:
        lines.append("Hydra command hook: command failed" if is_failed else "Hydra command hook: large command output summarized")
        if reduction.command:
            lines.append(f"Command: {reduction.command}")
        if is_failed and reduction.exit_code is not None:
            lines.append(f"Exit code: {reduction.exit_code}")
    lines.extend([
        f"Input lines: {reduction.input_line_count}",
        f"Input chars: {reduction.input_char_count}",
        f"Family: {reduction.family}",
        f"Reducer: {reduction.reducer_name}/v{reduction.reducer_version}",
        f"Summary: {reduction.compact_summary}",
    ])
    if raw_output_path:
        lines.append(f"Full log stored privately: {raw_output_path}")
    lines.append("Relevant excerpt:")
    has_selected_line = any(line.startswith("L") for line in reduction.important_lines)
    if has_selected_line:
        lines.extend(reduction.important_lines)
    elif reduction.has_reducer:
        lines.append("<no signal lines selected>")
        lines.extend(line for line in reduction.important_lines if line.startswith("... omitted "))
    else:
        lines.append("<no reviewed reducer matched; raw output omitted>")
    return "\n".join(lines)


def reduction_contract(reduction: Reduction, *, raw_output_path: str = "") -> dict:
    return {
        "schema": reduction.schema,
        "session_id": reduction.session_id,
        "key": reduction.key,
        "provider": reduction.provider,
        "tool_name": reduction.tool_name,
        "command": reduction.command,
        "cwd": reduction.cwd,
        "exit_code": reduction.exit_code,
        "output": {"kind": "combined", "line_count": reduction.input_line_count, "char_count": reduction.input_char_count},
        "family": reduction.family,
        "reducer": {"name": reduction.reducer_name, "version": reduction.reducer_version},
        "compact_summary": reduction.compact_summary,
        "important_lines": list(reduction.important_lines),
        "omitted": {"lines": reduction.omitted_lines, "chars": reduction.omitted_chars},
        "raw_output_path": raw_output_path,
    }
