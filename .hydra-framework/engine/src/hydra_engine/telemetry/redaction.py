"""Provider-neutral telemetry redaction contract.

This module deliberately does not collect telemetry. It is the field-level gate
required before any spend, session, or subagent capture path can
write records.
"""

from __future__ import annotations

import dataclasses
import hashlib
import re
from enum import Enum
from typing import Any


class FieldClassification(str, Enum):
    CAPTURED_VERBATIM = "captured verbatim"
    STRIPPED = "stripped"
    HASHED = "hashed"
    AGGREGATED_ONLY = "aggregated only"
    PRIVATE_SPILLOVER_ONLY = "private spillover only"
    DROPPED_ENTIRELY = "dropped entirely"


@dataclasses.dataclass(frozen=True)
class FieldPolicy:
    classification: FieldClassification
    reason: str


@dataclasses.dataclass(frozen=True)
class RedactionResult:
    shared: dict[str, Any]
    private_spillover: dict[str, Any]
    dropped: tuple[str, ...]


VERBATIM_FIELDS = {
    "at",
    "started_at",
    "ended_at",
    "generated_at",
    "retention_days",
    "agent_type",
    "model",
    "models",
    "status",
    "prompt_chars",
    "result_chars",
    "total_tokens",
    "input_tokens",
    "output_tokens",
    "cache_read_tokens",
    "cache_creation_tokens",
    "turns",
    "tool_calls",
    "reads",
    "searches",
    "bash_calls",
    "duration_ms",
    "provider",
    "command_head",
    "command_family",
    "reducer_name",
    "reducer_version",
    "exit_code",
    "input_line_count",
    "input_char_count",
    "omitted_line_count",
    "omitted_char_count",
    "had_reducer",
    "injector_matched",
    "injected",
    "event_schema",
    "event_kind",
    "command_id",
    "route_result",
    "package_count",
    "match_reason",
    "reference_count",
    "suppressed",
    "session_id_hash",
    "agent_id_hash",
}

HASHED_FIELDS = {"session_id", "agent_id"}

STRIPPED_FIELDS = {
    "hook_event_name",
    "tool_name",
    "tool_use_id",
    "turn_id",
    "permission_mode",
    "cwd",
    "transcript_path",
    "subagent_path",
    "session_path",
}

AGGREGATED_ONLY_FIELDS = {"subagent_records", "session_records"}

PRIVATE_SPILLOVER_ONLY_FIELDS = {
    "prompt",
    "result",
    "content",
    "tool_input",
    "tool_response",
    "raw_payload",
    "transcript_text",
    "transcript_rows",
    "assistant_usage_entries",
    "last_assistant_message",
    "command_output",
    "private_file_contents",
}

DROPPED_ENTIRELY_FIELDS = {"data.js", "dashboard_data", "dashboard.html"}


FIELD_POLICIES: dict[str, FieldPolicy] = {
    **{
        field: FieldPolicy(FieldClassification.CAPTURED_VERBATIM, "structural scalar safe only when poison-free")
        for field in VERBATIM_FIELDS
    },
    **{field: FieldPolicy(FieldClassification.HASHED, "stable provider or run identifier") for field in HASHED_FIELDS},
    **{field: FieldPolicy(FieldClassification.STRIPPED, "provider envelope or local path, not shared evidence") for field in STRIPPED_FIELDS},
    **{
        field: FieldPolicy(FieldClassification.AGGREGATED_ONLY, "raw record arrays are too identifying for shared telemetry")
        for field in AGGREGATED_ONLY_FIELDS
    },
    **{
        field: FieldPolicy(FieldClassification.PRIVATE_SPILLOVER_ONLY, "raw content or transcript material")
        for field in PRIVATE_SPILLOVER_ONLY_FIELDS
    },
    **{field: FieldPolicy(FieldClassification.DROPPED_ENTIRELY, "derived dashboard artifact, not telemetry") for field in DROPPED_ENTIRELY_FIELDS},
}

_ABSOLUTE_PATH_RE = re.compile(r"(?:^|\s)(?:/[A-Za-z0-9_.-]+(?:/[^\s`'\")\]]*)+|[A-Za-z]:\\[^\s`'\")\]]+)")
_EMAIL_RE = re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b")
_SECRET_RE = re.compile(
    r"(?i)(?:api[_-]?key|password|passwd|secret|token|authorization)\s*[:=]|"
    r"sk-[A-Za-z0-9_-]{8,}|AKIA[0-9A-Z]{16}|BEGIN [A-Z ]*PRIVATE KEY"
)
_CUSTOMER_RE = re.compile(r"(?i)\b(?:customer|tenant|guest|patient)[-_ ]?(?:name|email|id)?\b\s*[:=]")
_PRIVATE_FIXTURE_RE = re.compile(r"HYDRA_PRIVATE_FIXTURE|PRIVATE FILE CONTENT")


def classification_for(field: str) -> FieldClassification | None:
    policy = FIELD_POLICIES.get(field)
    return policy.classification if policy else None


def redact_shared_payload(payload: dict[str, Any], *, salt: bytes | str = b"") -> RedactionResult:
    """Return shared-safe fields plus private spillover for everything unsafe.

    Unknown fields fail closed to private spillover. Fields classified as
    aggregate-only are omitted from the event row because this helper has no
    aggregation window; aggregators may consume them before calling this helper.
    """
    shared: dict[str, Any] = {}
    spillover: dict[str, Any] = {}
    dropped: list[str] = []

    for field, value in payload.items():
        classification = classification_for(field)
        if classification is None:
            spillover[field] = value
        elif classification == FieldClassification.CAPTURED_VERBATIM:
            if contains_unsafe_content(value):
                spillover[field] = value
            else:
                shared[field] = value
        elif classification == FieldClassification.HASHED:
            if contains_unsafe_content(value):
                spillover[field] = value
            else:
                shared[f"{field}_hash"] = hash_identifier(value, salt=salt)
        elif classification == FieldClassification.STRIPPED:
            dropped.append(field)
        elif classification == FieldClassification.AGGREGATED_ONLY:
            dropped.append(field)
        elif classification == FieldClassification.PRIVATE_SPILLOVER_ONLY:
            spillover[field] = value
        elif classification == FieldClassification.DROPPED_ENTIRELY:
            dropped.append(field)
    return RedactionResult(shared=shared, private_spillover=spillover, dropped=tuple(sorted(dropped)))


def hash_identifier(value: Any, *, salt: bytes | str = b"") -> str:
    raw = str(value).encode("utf-8", errors="replace")
    key = salt.encode("utf-8") if isinstance(salt, str) else salt
    if len(key) > 64:
        key = hashlib.sha256(key).digest()
    digest = hashlib.blake2b(raw, key=key, digest_size=16)
    return digest.hexdigest()


def contains_unsafe_content(value: Any) -> bool:
    if isinstance(value, str):
        return any(
            pattern.search(value)
            for pattern in (_ABSOLUTE_PATH_RE, _EMAIL_RE, _SECRET_RE, _CUSTOMER_RE, _PRIVATE_FIXTURE_RE)
        )
    if isinstance(value, dict):
        return any(contains_unsafe_content(key) or contains_unsafe_content(item) for key, item in value.items())
    if isinstance(value, (list, tuple, set)):
        return any(contains_unsafe_content(item) for item in value)
    return False
