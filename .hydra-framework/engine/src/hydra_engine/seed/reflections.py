"""Reflection-queue packet parsing and validation.

Modeled on `seed/adaptations.py`'s split between a text parser, an entry
validator, and a thin file-level entry point -- the existing precedent for
validating an `evolution/` artifact. The packet header is `Key: value` lines,
not YAML frontmatter, parsed the same way `parse_adaptation_ledger_text`
parses its own header lines: literal prefix matching, so a human can hand-
edit a packet and the executable contract stays small.
"""

from __future__ import annotations

import re
from datetime import date, timedelta
from pathlib import Path

from hydra_engine.documents.tokens import display_path, read_text
from hydra_engine.finding import Finding
from hydra_engine.knowledge.candidates import APPROX_CHARS_PER_TOKEN, approx_tokens

REFLECTION_STATUSES = {"open", "held"}

REQUIRED_HEADER_FIELDS = ("Status", "Author", "Created", "Updated", "Scope")
REQUIRED_SECTIONS = ("## Observation", "## Evidence", "## Suggested Outcome")
HEADER_FIELDS = REQUIRED_HEADER_FIELDS + ("Held-Until",)

FILENAME_RE = re.compile(r"^(\d{4}-\d{2}-\d{2})-[a-z0-9-]+\.md$")

# Drain-pressure policy. All three are TEAM_TUNABLE_POLICY in
# thresholds.py: drain-pressure tuning a forking team should be able to set,
# not an engine invariant.
REFLECTION_PACKET_FAIL_TOKENS = 1200
REFLECTION_QUEUE_DEPTH_NOTE = 20
STALE_REFLECTION_DAYS = 30


def parse_reflection_packet_text(text: str, chars_per_token: int = APPROX_CHARS_PER_TOKEN) -> dict:
    """Parse one packet's header fields and section headings.

    Header fields are only recognized above the first `## ` section heading,
    so a field-shaped line inside `## Evidence` prose is never mistaken for
    the packet's own header.
    """
    lines = text.splitlines()
    header_lines: list[str] = []
    for line in lines:
        if line.startswith("## "):
            break
        header_lines.append(line)

    fields: dict[str, str] = {}
    for raw in header_lines:
        stripped = raw.strip()
        for field in HEADER_FIELDS:
            prefix = f"{field}:"
            if stripped.startswith(prefix):
                fields[field] = stripped[len(prefix):].strip()
                break

    sections = {line.strip() for line in lines if line.strip() in REQUIRED_SECTIONS}
    return {"fields": fields, "sections": sections, "token_count": approx_tokens(text, chars_per_token)}


def validate_reflection_packet(
    entry: dict,
    path_label: str,
    fail_tokens: int = REFLECTION_PACKET_FAIL_TOKENS,
) -> list[Finding]:
    findings: list[Finding] = []

    def add(detail: str) -> None:
        findings.append(Finding(path=path_label, code="reflection-queue", detail=detail))

    filename = Path(path_label).name
    match = FILENAME_RE.match(filename)
    if not match:
        add(f"{path_label}: filename must be `YYYY-MM-DD-slug.md`")
    else:
        try:
            date.fromisoformat(match.group(1))
        except ValueError:
            add(f"{path_label}: filename date `{match.group(1)}` is not a valid date")

    fields = entry.get("fields", {})
    for field in REQUIRED_HEADER_FIELDS:
        if not fields.get(field, "").strip():
            add(f"{path_label}: missing `{field}:`")

    status = fields.get("Status", "").strip()
    if status and status not in REFLECTION_STATUSES:
        add(f"{path_label}: `Status:` must be one of {sorted(REFLECTION_STATUSES)}")

    held_until = fields.get("Held-Until", "").strip()
    if status == "held":
        if not held_until:
            add(f"{path_label}: `Status: held` requires `Held-Until:`")
        else:
            try:
                date.fromisoformat(held_until)
            except ValueError:
                add(f"{path_label}: `Held-Until:` is not a valid `YYYY-MM-DD` date")
    elif status == "open" and held_until:
        add(f"{path_label}: `Status: open` must not carry `Held-Until:`")

    for date_field in ("Created", "Updated"):
        value = fields.get(date_field, "").strip()
        if value:
            try:
                date.fromisoformat(value)
            except ValueError:
                add(f"{path_label}: `{date_field}:` is not a valid `YYYY-MM-DD` date")

    for heading in REQUIRED_SECTIONS:
        if heading not in entry.get("sections", set()):
            add(f"{path_label}: missing `{heading}` section")

    token_count = entry.get("token_count", 0)
    if token_count > fail_tokens:
        add(f"{path_label}: {token_count} approx tokens exceeds the {fail_tokens}-token ceiling")

    return findings


def _packet_paths(reflections_dir: Path) -> list[Path]:
    if not reflections_dir.exists():
        return []
    return [path for path in sorted(reflections_dir.glob("*.md")) if path.name != "README.md"]


def validate_reflection_queue(
    reflections_dir: Path,
    root: Path,
    fail_tokens: int = REFLECTION_PACKET_FAIL_TOKENS,
    chars_per_token: int = APPROX_CHARS_PER_TOKEN,
) -> list[Finding]:
    """Enforce packet shape. An absent directory is valid: nothing is filed yet."""
    findings: list[Finding] = []
    for path in _packet_paths(reflections_dir):
        entry = parse_reflection_packet_text(read_text(path), chars_per_token)
        findings.extend(validate_reflection_packet(entry, display_path(path, root), fail_tokens))
    return findings


def reflection_queue_notes(
    reflections_dir: Path,
    root: Path,
    today: str,
    stale_days: int = STALE_REFLECTION_DAYS,
    depth_note: int = REFLECTION_QUEUE_DEPTH_NOTE,
) -> list[str]:
    """Advisory observations about the reflection queue's drain state.

    These are notes, not errors -- a check that blocks work for bookkeeping is
    one people route around (placement rules). A packet cannot trigger both the
    staleness note and the overdue-hold note: `open` packets are checked
    against `Created:`, `held` packets against their own `Held-Until:`.
    """
    notes: list[str] = []
    packets = _packet_paths(reflections_dir)
    today_date = date.fromisoformat(today)
    stale_cutoff = today_date - timedelta(days=stale_days)

    for path in packets:
        fields = parse_reflection_packet_text(read_text(path)).get("fields", {})
        status = fields.get("Status", "").strip()
        label = display_path(path, root)
        if status == "open":
            created = fields.get("Created", "").strip()
            try:
                if created and date.fromisoformat(created) < stale_cutoff:
                    notes.append(f"{label}: open reflection packet filed {created}, past the {stale_days}-day drain expectation")
            except ValueError:
                pass  # malformed date is already a `validate_reflection_queue` error
        elif status == "held":
            held_until = fields.get("Held-Until", "").strip()
            try:
                if held_until and date.fromisoformat(held_until) < today_date:
                    notes.append(f"{label}: held reflection packet is past its `Held-Until: {held_until}`")
            except ValueError:
                pass  # malformed date is already a `validate_reflection_queue` error

    if len(packets) > depth_note:
        notes.append(
            f"evolution/reflections/: {len(packets)} packets pending, above the "
            f"{depth_note}-packet readability backstop"
        )
    return notes
