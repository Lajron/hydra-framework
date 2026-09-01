"""Transcript-derived session aggregate telemetry."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from hydra_engine.documents.tokens import read_text
from hydra_engine.telemetry import writer


def capture_claude_session_aggregate(local: Path, hook_payload: dict[str, Any]) -> writer.CapturedTelemetry | None:
    return capture_session_aggregate(local, hook_payload, provider="claude")


def capture_codex_session_aggregate(local: Path, hook_payload: dict[str, Any]) -> writer.CapturedTelemetry | None:
    return capture_session_aggregate(local, hook_payload, provider="codex")


def capture_session_aggregate(local: Path, hook_payload: dict[str, Any], *, provider: str) -> writer.CapturedTelemetry | None:
    transcript = _transcript_path_from_payload(hook_payload)
    if not isinstance(transcript, str) or not transcript:
        return None
    aggregate = session_aggregate(Path(transcript), provider=provider, session_id=str(hook_payload.get("session_id") or ""))
    if aggregate is None:
        return None
    return writer.write_event(local, aggregate)


def claude_session_aggregate(path: Path, *, provider: str, session_id: str = "") -> dict[str, Any] | None:
    return session_aggregate(path, provider=provider, session_id=session_id)


def codex_session_aggregate(path: Path, *, provider: str, session_id: str = "") -> dict[str, Any] | None:
    return session_aggregate(path, provider=provider, session_id=session_id)


def session_aggregate(path: Path, *, provider: str, session_id: str = "") -> dict[str, Any] | None:
    totals = {"input_tokens": 0, "output_tokens": 0, "cache_read_tokens": 0, "cache_creation_tokens": 0}
    models: set[str] = set()
    turns = 0
    try:
        lines = read_text(path).splitlines()
    except OSError:
        return None
    for line in lines:
        row = _json_object(line)
        usage = _usage_from_row(row)
        if not usage:
            continue
        turns += 1
        totals["input_tokens"] += _int_value(usage, "input_tokens", "prompt_tokens")
        totals["output_tokens"] += _int_value(usage, "output_tokens", "completion_tokens")
        totals["cache_read_tokens"] += _int_value(usage, "cache_read_tokens", "cache_read_input_tokens", "cached_input_tokens")
        totals["cache_creation_tokens"] += _int_value(
            usage,
            "cache_creation_tokens",
            "cache_creation_input_tokens",
            "cache_write_input_tokens",
        )
        model = _model_from_row(row)
        if model:
            models.add(model)
    if turns == 0:
        return None
    event: dict[str, Any] = {
        "event_kind": "session.aggregate",
        "provider": provider,
        "turns": turns,
        **totals,
        "total_tokens": sum(totals.values()),
    }
    if session_id:
        event["session_id"] = session_id
    if len(models) == 1:
        event["model"] = next(iter(models))
    elif models:
        event["models"] = sorted(models)
    return event


def _transcript_path_from_payload(hook_payload: dict[str, Any]) -> str:
    for field in ("transcript_path", "session_path"):
        value = hook_payload.get(field)
        if isinstance(value, str) and value:
            return value
    return ""


def _usage_from_row(row: dict[str, Any]) -> dict[str, Any]:
    payload = row.get("payload")
    if isinstance(payload, dict) and payload.get("type") == "token_count":
        info = payload.get("info")
        if isinstance(info, dict) and isinstance(info.get("last_token_usage"), dict):
            return info["last_token_usage"]
    message = row.get("message")
    if isinstance(message, dict) and isinstance(message.get("usage"), dict):
        return message["usage"]
    usage = row.get("usage")
    return usage if isinstance(usage, dict) else {}


def _model_from_row(row: dict[str, Any]) -> str:
    message = row.get("message")
    if isinstance(message, dict) and isinstance(message.get("model"), str):
        return message["model"]
    payload = row.get("payload")
    if isinstance(payload, dict):
        for field in ("model", "model_slug"):
            model = payload.get(field)
            if isinstance(model, str):
                return model
    model = row.get("model")
    return model if isinstance(model, str) else ""


def _int_value(mapping: dict[str, Any], *keys: str) -> int:
    for key in keys:
        value = mapping.get(key)
        if isinstance(value, int) and not isinstance(value, bool):
            return value
    return 0


def _json_object(line: str) -> dict[str, Any]:
    try:
        value = json.loads(line)
    except ValueError:
        return {}
    return value if isinstance(value, dict) else {}
