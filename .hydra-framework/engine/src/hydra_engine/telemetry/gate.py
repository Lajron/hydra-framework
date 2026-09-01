"""Redaction gate for private local telemetry rows."""

from __future__ import annotations

import dataclasses
import hashlib
from pathlib import Path
from typing import Any

from hydra_engine.ports import clock
from hydra_engine.telemetry import redaction, writer

GATE_MAX_SPILLOVER_PER_1000 = 50
GATE_MIN_EVENT_COUNT = 3
GATE_MIN_EVENT_KINDS = 3

POISON = "HYDRA_PRIVATE_FIXTURE password=secret"


@dataclasses.dataclass(frozen=True)
class GateAttestation:
    verdict: str
    date: str
    event_count: int
    distinct_event_kinds: tuple[str, ...]
    distinct_field_names: tuple[str, ...]
    redaction_digest: str
    spillover_per_1000: int
    failures: tuple[str, ...]

    def as_dict(self) -> dict[str, Any]:
        return dataclasses.asdict(self)


def run_gate(
    *,
    local: Path,
    hydra: Path,
    max_spillover_per_1000: int = GATE_MAX_SPILLOVER_PER_1000,
    min_event_count: int = GATE_MIN_EVENT_COUNT,
    min_event_kinds: int = GATE_MIN_EVENT_KINDS,
) -> GateAttestation:
    rows = _synthetic_rows() + list(writer.iter_event_rows(local))
    failures: list[str] = []
    field_names = tuple(sorted({field for row in rows for field in row}))
    event_kinds = tuple(sorted({str(row.get("event_kind")) for row in rows if row.get("event_kind")}))
    unclassified = sorted(field for field in field_names if not _classified_shared_field(field))
    if unclassified:
        failures.append(f"unclassified shared fields: {', '.join(unclassified)}")

    total_fields = sum(len(row) for row in rows)
    spillover_fields = 0
    for row in rows:
        result = redaction.redact_shared_payload(row, salt="gate")
        spillover_fields += len(result.private_spillover)
        failures.extend(_poison_failures(row))
    spillover_per_1000 = int((spillover_fields * 1000) / total_fields) if total_fields else 1000

    if spillover_per_1000 > max_spillover_per_1000:
        failures.append(f"spillover rate {spillover_per_1000}/1000 exceeds {max_spillover_per_1000}/1000")
    if len(rows) < min_event_count:
        failures.append(f"event count {len(rows)} below minimum {min_event_count}")
    if len(event_kinds) < min_event_kinds:
        failures.append(f"distinct event kinds {len(event_kinds)} below minimum {min_event_kinds}")
    return GateAttestation(
        verdict="fail" if failures else "pass",
        date=clock.today(),
        event_count=len(rows),
        distinct_event_kinds=event_kinds,
        distinct_field_names=field_names,
        redaction_digest=redaction_digest(hydra),
        spillover_per_1000=spillover_per_1000,
        failures=tuple(failures),
    )


def _poison_failures(row: dict[str, Any]) -> list[str]:
    failures: list[str] = []
    for field in row:
        poisoned = dict(row)
        poisoned[field] = POISON
        result = redaction.redact_shared_payload(poisoned, salt="gate")
        if field not in result.private_spillover:
            failures.append(f"poison did not spill from `{field}`")
    return failures


def _classified_shared_field(field: str) -> bool:
    return redaction.classification_for(field) is not None


def redaction_digest(hydra: Path) -> str:
    path = hydra / "engine/src/hydra_engine/telemetry/redaction.py"
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _synthetic_rows() -> list[dict[str, Any]]:
    return [
        {
            "event_schema": writer.EVENT_SCHEMA,
            "at": "2026-08-28T00:00:00Z",
            "event_kind": "command.invocation",
            "command_id": "validate",
        },
        {
            "event_schema": writer.EVENT_SCHEMA,
            "at": "2026-08-28T00:00:00Z",
            "event_kind": "command_output.reducer_outcome",
            "provider": "claude",
            "command_head": "dotnet",
            "exit_code": 1,
            "command_family": "dotnet-build",
            "reducer_name": "dotnet-build",
            "reducer_version": "1",
            "input_line_count": 10,
            "input_char_count": 1000,
            "omitted_line_count": 2,
            "omitted_char_count": 200,
            "had_reducer": True,
            "session_id_hash": "0123456789abcdef0123456789abcdef",
        },
        {
            "event_schema": writer.EVENT_SCHEMA,
            "at": "2026-08-28T00:00:00Z",
            "event_kind": "session.aggregate",
            "provider": "claude",
            "turns": 2,
            "input_tokens": 10,
            "output_tokens": 20,
            "cache_read_tokens": 30,
            "cache_creation_tokens": 40,
            "total_tokens": 100,
        },
    ]
