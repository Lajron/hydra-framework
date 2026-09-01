"""Command-output reducer telemetry payload shaping."""

from __future__ import annotations

from hydra_engine.command_output.model import Reduction
from hydra_engine.command_output.shell import parse_command
from hydra_engine.telemetry import transcripts
from hydra_engine.telemetry import writer
from hydra_engine.telemetry.redaction import RedactionResult, redact_shared_payload


def structural_payload(reduction: Reduction) -> dict:
    parsed = parse_command(reduction.command)
    return {
        "event_kind": "command_output.reducer_outcome",
        "session_id": reduction.session_id,
        "provider": reduction.provider,
        "command_head": parsed.head,
        "exit_code": reduction.exit_code,
        "command_family": reduction.family,
        "reducer_name": reduction.reducer_name,
        "reducer_version": reduction.reducer_version,
        "input_line_count": reduction.input_line_count,
        "input_char_count": reduction.input_char_count,
        "omitted_line_count": reduction.omitted_lines,
        "omitted_char_count": reduction.omitted_chars,
        "had_reducer": reduction.has_reducer,
    }


def redact_reducer_event(reduction: Reduction, *, salt: bytes | str = b"") -> RedactionResult:
    return redact_shared_payload(structural_payload(reduction), salt=salt)


def record_reducer_event(local, reduction: Reduction) -> writer.CapturedTelemetry:
    return writer.write_event(local, structural_payload(reduction))


def capture_session_aggregate(local, provider: str, payload: dict) -> writer.CapturedTelemetry | None:
    return transcripts.capture_session_aggregate(local, payload, provider=provider)


def capture_claude_session_aggregate(local, payload: dict) -> writer.CapturedTelemetry | None:
    return transcripts.capture_claude_session_aggregate(local, payload)


def capture_codex_session_aggregate(local, payload: dict) -> writer.CapturedTelemetry | None:
    return transcripts.capture_codex_session_aggregate(local, payload)
