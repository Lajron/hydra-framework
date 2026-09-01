"""Evolution-candidates queue governance.

Modeled on `seed/reflections.py`'s split between a text parser, an entry
validator, and thin file-level entry points -- the same precedent
for validating an `evolution/` artifact. Candidates differ from reflection
packets in one essential way: a candidate's terminal state is a status
value, never file deletion. An accepted, rejected, captured, or superseded
candidate is the durable record of a decision this repository already made;
deleting it would only recreate the reflection queue's own reason for
existing -- an observation nobody can find again. Only `proposed` (a
candidate awaiting that decision) is non-terminal.
"""

from __future__ import annotations

from datetime import date, timedelta
from pathlib import Path

from hydra_engine.documents.tokens import display_path, read_text
from hydra_engine.finding import Finding

CANDIDATE_STATUSES = {"proposed", "accepted", "rejected", "captured", "superseded"}
NON_TERMINAL_CANDIDATE_STATUSES = {"proposed"}

REQUIRED_HEADER_FIELDS = ("Status", "Author", "Created")

# Drain-pressure policy, mirroring the reflection-
# queue precedent. TEAM_TUNABLE_POLICY in thresholds.py: a forking team should
# be able to set its own patience for an undecided proposal.
STALE_PROPOSED_CANDIDATE_DAYS = 30


def parse_candidate_header(text: str) -> dict[str, str]:
    """Parse only the header lines above the first `## ` section heading, so a
    field-shaped line inside a body section is never mistaken for the header.
    """
    fields: dict[str, str] = {}
    for line in text.splitlines():
        if line.startswith("## "):
            break
        stripped = line.strip()
        for field in REQUIRED_HEADER_FIELDS:
            prefix = f"{field}:"
            if stripped.startswith(prefix):
                fields[field] = stripped[len(prefix):].strip()
                break
    return fields


def validate_candidate_file(fields: dict[str, str], path_label: str) -> list[Finding]:
    findings: list[Finding] = []

    def add(detail: str) -> None:
        findings.append(Finding(path=path_label, code="candidate-queue", detail=detail))

    for field in REQUIRED_HEADER_FIELDS:
        if not fields.get(field, "").strip():
            add(f"{path_label}: missing `{field}:`")

    status = fields.get("Status", "").strip()
    if status and status not in CANDIDATE_STATUSES:
        add(f"{path_label}: `Status:` must be one of {sorted(CANDIDATE_STATUSES)}")

    created = fields.get("Created", "").strip()
    if created:
        try:
            date.fromisoformat(created)
        except ValueError:
            add(f"{path_label}: `Created:` is not a valid `YYYY-MM-DD` date")

    return findings


def _candidate_paths(candidates_dir: Path) -> list[Path]:
    """Direct `*.md` children only. A split candidate's own subdirectory (for
    example `2026-08-12-base-upgrade-plan/`) holds part files the router file
    already accounts for, not separate queue entries.
    """
    if not candidates_dir.is_dir():
        return []
    return [path for path in sorted(candidates_dir.glob("*.md")) if path.name != "README.md"]


def validate_candidate_queue(candidates_dir: Path, root: Path) -> list[Finding]:
    """Enforce the header contract. An absent directory is valid: nothing filed yet."""
    findings: list[Finding] = []
    for path in _candidate_paths(candidates_dir):
        fields = parse_candidate_header(read_text(path))
        findings.extend(validate_candidate_file(fields, display_path(path, root)))
    return findings


def candidate_queue_notes(
    candidates_dir: Path,
    root: Path,
    today: str,
    stale_days: int = STALE_PROPOSED_CANDIDATE_DAYS,
) -> list[str]:
    """Advisory forcing signal: an undecided proposal ages into a note, not a
    build failure -- a check that blocks work for bookkeeping is one people
    route around (placement rules). Only `proposed` items are checked; a
    terminal status already answered the question a note would raise.
    """
    notes: list[str] = []
    today_date = date.fromisoformat(today)
    cutoff = today_date - timedelta(days=stale_days)

    for path in _candidate_paths(candidates_dir):
        fields = parse_candidate_header(read_text(path))
        status = fields.get("Status", "").strip()
        if status not in NON_TERMINAL_CANDIDATE_STATUSES:
            continue
        created = fields.get("Created", "").strip()
        label = display_path(path, root)
        try:
            if created and date.fromisoformat(created) < cutoff:
                notes.append(
                    f"{label}: `Status: proposed` since {created}, past the "
                    f"{stale_days}-day decision expectation"
                )
        except ValueError:
            pass  # malformed date is already a `validate_candidate_queue` error
    return notes
