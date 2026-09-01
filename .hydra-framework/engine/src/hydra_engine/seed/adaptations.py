"""Adaptation-ledger parsing, validation, and authoring.

`current_base_seed_version` takes the already-parsed `manifest.yaml` dict as
a parameter rather than parsing it itself: importing `documents.yaml_documents`
here for `parse_yaml`/`yaml_map`/`yaml_str` would have been this module's own
new import of a module already at in-degree 10 (the cap check 4 enforces),
matching `installation.adopt`'s precedent for the identical interaction.
`hydra.py`'s `parse_yaml()` wrapper computes `manifest` once; this module
reimplements the two trivial value-coercion shapes locally (`_as_map`/
`_as_str`) instead of importing the module for them alone. `lineage_block`
(a `hydra.py`-only one-liner with two other real callers) is not called from
here for the same upward-import reason -- its `yaml_map(manifest.get(...))`
shape is reimplemented inline instead.
"""

from __future__ import annotations

import re
from datetime import date
from pathlib import Path

from hydra_engine.documents.tokens import display_path, read_text
from hydra_engine.finding import Finding
from hydra_engine.ports import fs

ADAPTATION_LIST_SECTIONS = {
    "Paths touched:": "paths_touched",
    "Why:": "why",
    "Evidence:": "evidence",
}

ADAPTATION_DISPOSITIONS = {"repo-local", "promote-candidate"}


def _as_map(value: object) -> dict:
    return value if isinstance(value, dict) else {}


def _as_str(value: object, fallback: str = "") -> str:
    return value if isinstance(value, str) else fallback


def normalize_adaptation_path(value: str) -> str:
    """Ledger paths are written repository-relative; `diff-base` reports them
    relative to `.hydra-framework/`. Compare both in the same terms."""
    return value.strip().removeprefix(".hydra-framework/")


def parse_adaptation_ledger_text(text: str) -> list[dict]:
    """Parse Hydra's append-only adaptation ledger.

    The ledger is Markdown on purpose: a human can append and review entries by
    hand, and the executable contract stays small enough to check without
    parsing free-form rationale as YAML.
    """
    entries: list[dict] = []
    current: dict | None = None
    section = ""

    for raw in text.splitlines():
        stripped = raw.strip()
        if raw.startswith("## "):
            current = {
                "heading": stripped[3:].strip(),
                "base_seed_version": "",
                "disposition": "",
                "paths_touched": [],
                "why": [],
                "evidence": [],
            }
            entries.append(current)
            section = ""
        elif current is None:
            continue
        elif stripped.startswith("Base seed version:"):
            current["base_seed_version"] = stripped.partition(":")[2].strip()
            section = ""
        elif stripped.startswith("Disposition:"):
            current["disposition"] = stripped.partition(":")[2].strip()
            section = ""
        elif stripped in ADAPTATION_LIST_SECTIONS:
            section = ADAPTATION_LIST_SECTIONS[stripped]
        elif section and stripped.startswith("- "):
            current[section].append(stripped[2:].strip())
    return entries


def validate_adaptation_entries(entries: list[dict], path_label: str) -> list[Finding]:
    findings: list[Finding] = []

    def add(detail: str) -> None:
        findings.append(Finding(path=path_label, code="adaptations-ledger", detail=detail))

    for index, entry in enumerate(entries, start=1):
        heading = entry.get("heading", "")
        label = heading or f"entry {index}"
        match = re.match(r"^(\d{4}-\d{2}-\d{2}) - .+", heading)
        if not match:
            add(f"{path_label} entry {index} heading must be `YYYY-MM-DD - title`")
        else:
            try:
                date.fromisoformat(match.group(1))
            except ValueError:
                add(f"{path_label} `{label}` has invalid date `{match.group(1)}`")

        if not entry.get("base_seed_version", "").strip():
            add(f"{path_label} `{label}` missing `Base seed version:`")
        if entry.get("disposition", "").strip() not in ADAPTATION_DISPOSITIONS:
            add(f"{path_label} `{label}` disposition must be one of {sorted(ADAPTATION_DISPOSITIONS)}")
        for key, title in ADAPTATION_LIST_SECTIONS.items():
            if not [value for value in entry.get(title, []) if value.strip()]:
                add(f"{path_label} `{label}` missing `{key}` bullet(s)")
    return findings


def validate_adaptations_ledger(ledger_path: Path, root: Path) -> list[Finding]:
    """Enforce entry shape. An absent ledger is valid: nothing has diverged yet."""
    if not ledger_path.exists():
        return []
    entries = parse_adaptation_ledger_text(read_text(ledger_path))
    return validate_adaptation_entries(entries, display_path(ledger_path, root))


def ledger_entries_for_path(path: str, entries: list[dict]) -> list[str]:
    matches = []
    for entry in entries:
        touched = {normalize_adaptation_path(item) for item in entry.get("paths_touched", [])}
        if path in touched and entry.get("heading"):
            matches.append(entry["heading"])
    return matches


def format_adaptation_entry(
    *,
    date_value: str,
    title: str,
    base_seed_version: str,
    paths: list[str],
    why: list[str],
    evidence: list[str],
    disposition: str,
) -> str:
    lines = [
        f"## {date_value} - {title}",
        "",
        f"Base seed version: {base_seed_version}",
        f"Disposition: {disposition}",
        "Paths touched:",
    ]
    lines.extend(f"- {normalize_adaptation_path(path)}" for path in paths)
    lines.extend(["Why:"])
    lines.extend(f"- {item.strip()}" for item in why)
    lines.extend(["Evidence:"])
    lines.extend(f"- {item.strip()}" for item in evidence)
    return "\n".join(lines).rstrip() + "\n"


def append_adaptation_entry(ledger_path: Path, entry: str) -> None:
    """Append one entry without a read-modify-write: two concurrent
    adaptation records can only ever both land, never have one clobber the
    other."""
    fs.create_exclusive(ledger_path, "# Adaptations Ledger\n")
    fs.append_line(ledger_path, "\n" + entry.rstrip() + "\n")


def current_base_seed_version(manifest: dict) -> str:
    lineage = _as_map(manifest.get("lineage"))
    return _as_str(lineage.get("base_seed_version")) or _as_str(manifest.get("seed_version"), "unknown")
