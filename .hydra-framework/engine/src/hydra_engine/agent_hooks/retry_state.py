"""Retry-failure fingerprint state.

Moved unchanged from `scripts/hydra.py`, with `LOCAL` replaced by an explicit
`AgentHooksPaths` argument per the "only the composition root knows the
repository root" rule.

Append-only: this is
the retry-count safety brake `AGENTS.md` relies on to halt a looping agent,
and the old read-modify-write (read the whole file, increment, write the
whole file back) silently lost an increment whenever two hook processes
raced, which is the normal case once an agent spawns subagents. Each failure
now appends one JSON line; the count for a fingerprint is the number of
lines recorded for it since its last reset tombstone, aggregated at read
time, so a concurrent writer can only add a line, never erase one.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

from hydra_engine.agent_hooks.logs import summarize_log_text
from hydra_engine.agent_hooks.paths import AgentHooksPaths
from hydra_engine.documents.tokens import display_path, read_text
from hydra_engine.ports import clock, fs

RETRY_FINGERPRINT_SUMMARY_LINES = 24
RETRY_FINGERPRINT_SAMPLE_CHARS = 4000
RETRY_FINGERPRINT_STORED_SAMPLE_CHARS = 3500
RETRY_STATE_GROWTH_ADVISORY_LINES = 5000

_RESET = "reset"
_FAILURE = "failure"


def retry_state_path(paths: AgentHooksPaths) -> Path:
    return paths.local / "monitoring" / "retry-state.jsonl"


def _events(path: Path) -> list[dict]:
    if not path.exists():
        return []
    events = []
    for line in read_text(path).splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            event = json.loads(line)
        except ValueError:
            continue
        if isinstance(event, dict) and event.get("fingerprint"):
            events.append(event)
    return events


def read_retry_state(path: Path) -> dict:
    """Aggregate every event since each fingerprint's last reset tombstone."""
    fingerprints: dict[str, dict] = {}
    for event in _events(path):
        fingerprint = event["fingerprint"]
        if event.get("event") == _RESET:
            fingerprints.pop(fingerprint, None)
            continue
        record = fingerprints.setdefault(fingerprint, {"count": 0, "first_seen": event.get("at", "")})
        record["count"] += 1
        record["last_seen"] = event.get("at", "")
        record["command"] = event.get("command", "")
        record["exit_code"] = event.get("exit_code")
        record["key"] = event.get("key", "")
        record["sample"] = event.get("sample", "")
    return {"fingerprints": fingerprints}


def retry_fingerprint(command: str, exit_code: int | None, text: str, key: str) -> tuple[str, str]:
    summary = "\\n".join(summarize_log_text(text, RETRY_FINGERPRINT_SUMMARY_LINES)) if text else ""
    sample = summary[:RETRY_FINGERPRINT_SAMPLE_CHARS] or command
    material = f"{key}\\0{command}\\0{exit_code}\\0{sample}"
    return hashlib.sha256(material.encode("utf-8")).hexdigest(), sample


def record_retry_failure(paths: AgentHooksPaths, command: str, exit_code: int | None, text: str, key: str) -> tuple[str, dict]:
    path = retry_state_path(paths)
    fingerprint, sample = retry_fingerprint(command, exit_code, text, key)
    stored_sample = sample[:RETRY_FINGERPRINT_STORED_SAMPLE_CHARS]
    fs.append_line(path, json.dumps({
        "event": _FAILURE, "fingerprint": fingerprint, "at": clock.now_local_iso_seconds(),
        "command": command, "exit_code": exit_code, "key": key, "sample": stored_sample,
    }, sort_keys=True))
    record = read_retry_state(path)["fingerprints"][fingerprint]
    return fingerprint, record


def reset_retry_failure(paths: AgentHooksPaths, command: str, exit_code: int | None, text: str, key: str) -> bool:
    path = retry_state_path(paths)
    fingerprint, _sample = retry_fingerprint(command, exit_code, text, key)
    if fingerprint not in read_retry_state(path)["fingerprints"]:
        return False
    fs.append_line(path, json.dumps({
        "event": _RESET, "fingerprint": fingerprint, "at": clock.now_local_iso_seconds(),
    }, sort_keys=True))
    return True


def retry_state_growth_notes(paths: AgentHooksPaths, growth_advisory_lines: int = RETRY_STATE_GROWTH_ADVISORY_LINES) -> list[str]:
    """Advisory only: an append-only log is never compacted here (compaction
    is itself a read-modify-write, which is exactly the race this file's
    format was chosen to remove), so unbounded growth is expected and this
    only flags when it is worth a deliberate deletion. Deleting the file is
    safe; the retry counter simply restarts from zero."""
    path = retry_state_path(paths)
    if not path.exists():
        return []
    line_count = sum(1 for line in read_text(path).splitlines() if line.strip())
    if line_count <= growth_advisory_lines:
        return []
    return [
        f"{display_path(path, paths.root)}: {line_count} retry-state events recorded, above the "
        f"{growth_advisory_lines}-line advisory; delete the file to reset it, safe because the retry "
        "counter simply restarts from zero"
    ]
