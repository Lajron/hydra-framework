"""Private append-only telemetry writer.

Capture sites build provider-neutral event payloads and this module applies the
redaction contract before appending a shared-safe row to the private local
event log. Failed-closed fields are kept in a separate private spillover log.
"""

from __future__ import annotations

import dataclasses
import json
import os
from pathlib import Path
from typing import Any, Iterable

from hydra_engine.documents.tokens import display_path, read_text
from hydra_engine.ports import fs
from hydra_engine.telemetry.redaction import FieldClassification, classification_for, redact_shared_payload

EVENT_SCHEMA = "hydra.telemetry.event.v1"
EVENTS_FILE = "events.jsonl"
SPILLOVER_FILE = "spillover.jsonl"
SALT_FILE = "salt"
TELEMETRY_EVENTS_GROWTH_ADVISORY_LINES = 5000


@dataclasses.dataclass(frozen=True)
class CapturedTelemetry:
    shared: dict[str, Any]
    private_spillover: dict[str, Any]
    dropped: tuple[str, ...]


def telemetry_dir(local: Path) -> Path:
    return local / "telemetry"


def events_path(local: Path) -> Path:
    return telemetry_dir(local) / EVENTS_FILE


def spillover_path(local: Path) -> Path:
    return telemetry_dir(local) / SPILLOVER_FILE


def salt_path(local: Path) -> Path:
    return telemetry_dir(local) / SALT_FILE


def repository_salt(local: Path) -> str:
    path = salt_path(local)
    if path.exists():
        return read_text(path).strip()
    created = os.urandom(16).hex()
    fs.create_exclusive(path, created + "\n")
    return read_text(path).strip()


def write_event(local: Path, payload: dict[str, Any]) -> CapturedTelemetry:
    event = {"event_schema": EVENT_SCHEMA, **payload}
    result = redact_shared_payload(event, salt=_salt_for_payload(local, event))
    if result.shared:
        fs.append_line(events_path(local), _json_line(result.shared))
    if result.private_spillover:
        spillover = {
            "event_schema": EVENT_SCHEMA,
            "event_kind": event.get("event_kind", "unknown"),
            "fields": sorted(result.private_spillover),
            "payload": result.private_spillover,
        }
        fs.append_line(spillover_path(local), _json_line(spillover))
    return CapturedTelemetry(result.shared, result.private_spillover, result.dropped)


def iter_event_rows(local: Path) -> Iterable[dict[str, Any]]:
    path = events_path(local)
    if not path.exists():
        return
    for line in read_text(path).splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            event = json.loads(line)
        except ValueError:
            continue
        if isinstance(event, dict):
            yield event


def record_command_invocation(local: Path, command_id: str) -> CapturedTelemetry:
    return write_event(local, {"event_kind": "command.invocation", "command_id": command_id})


def record_knowledge_command_usage(local: Path, command: str) -> CapturedTelemetry:
    return write_event(local, {"event_kind": "knowledge.command_usage", "command_id": command})


def record_knowledge_route(
    local: Path,
    hit: bool,
    *,
    package_count: int = 0,
    match_reason: str = "",
    reference_count: int = 0,
    suppressed: bool = False,
) -> CapturedTelemetry:
    return write_event(local, {
        "event_kind": "knowledge.route",
        "route_result": "hit" if hit else "miss",
        "package_count": package_count,
        "match_reason": match_reason or "none",
        "reference_count": reference_count,
        "suppressed": suppressed,
    })


def knowledge_counts(local: Path) -> dict[str, dict[str, int]]:
    counts: dict[str, dict[str, int]] = {}
    for event in iter_event_rows(local):
        if event.get("event_kind") == "knowledge.command_usage":
            _increment(counts, "commands", event.get("command_id"))
        elif event.get("event_kind") == "knowledge.route":
            _increment(counts, "route", event.get("route_result"))
    return counts


def event_growth_notes(local: Path, root: Path, growth_advisory_lines: int) -> list[str]:
    path = events_path(local)
    if not path.exists():
        return []
    line_count = sum(1 for line in read_text(path).splitlines() if line.strip())
    if line_count <= growth_advisory_lines:
        return []
    return [
        f"{display_path(path, root)}: {line_count} telemetry events recorded, above the "
        f"{growth_advisory_lines}-line advisory; delete the file to reset local telemetry"
    ]


def _increment(counts: dict[str, dict[str, int]], bucket: str, raw_key: object) -> None:
    if not isinstance(raw_key, str) or not raw_key:
        return
    bucket_counts = counts.setdefault(bucket, {})
    bucket_counts[raw_key] = bucket_counts.get(raw_key, 0) + 1


def _json_line(value: dict[str, Any]) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"))


def _salt_for_payload(local: Path, payload: dict[str, Any]) -> str:
    if any(classification_for(field) == FieldClassification.HASHED for field in payload):
        return repository_salt(local)
    return ""
