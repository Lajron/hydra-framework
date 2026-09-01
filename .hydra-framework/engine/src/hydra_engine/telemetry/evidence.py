"""Telemetry evidence package queue governance.

Modeled on `seed/candidate_queue.py`'s split between a text parser, an entry
validator, and thin file-level entry points -- the same precedent
for validating a governed queue. Two things neither existing governed queue
has make this validator larger than either: an object envelope every
package carries, and three required files per entry rather than
one.

A package's terminal state is a status value, never file deletion, for the
same reason `evolution/candidates/` never deletes: an absorbing decision or
knowledge file cites the package by `hydra_id`, and deleting it would break
that citation and destroy the baseline a later re-measurement diffs against.
"""

from __future__ import annotations

import json
import re
from datetime import date, timedelta
from pathlib import Path
from typing import Any

from hydra_engine.documents.frontmatter_blocks import markdown_frontmatter, yaml_str
from hydra_engine.documents.tokens import HydraYamlError, display_path, read_text
from hydra_engine.finding import Finding
from hydra_engine.knowledge.candidates import APPROX_CHARS_PER_TOKEN, approx_tokens
from hydra_engine.telemetry.gate import GateAttestation, redaction_digest
from hydra_engine.telemetry.redaction import contains_unsafe_content

_CODE = "telemetry-evidence"

TELEMETRY_EVIDENCE_STATUSES = {"open", "absorbed", "superseded", "rejected"}
NON_TERMINAL_TELEMETRY_EVIDENCE_STATUSES = {"open"}

REQUIRED_HEADER_FIELDS = ("Author", "Created", "Window", "Corpus")
REQUIRED_SECTIONS = ("## Question", "## Findings", "## Method", "## Absorption")
REQUIRED_FILES = ("overview.md", "metrics.json", "gate-attestation.json")

_DIR_NAME_DATE_RE = re.compile(r"^(\d{4}-\d{2}-\d{2})-")
_SHORT_SLUG_RE = re.compile(r"^[a-z0-9-]+$")

# Matches the template's `Corpus: <count> events across <N> kinds` shape
# (evidence_mint.render_overview seeds this exact wording as a TODO). A
# `Corpus:` line in some other shape is not checked -- this only guards
# against the one drift pattern the template invites: hand-copying a later
# `telemetry report` run's numbers into the prose without regenerating
# metrics.json from that same run.
_CORPUS_RE = re.compile(r"^([\d,]+)\s+events?\s+across\s+(\d+)\s+kinds?\b", re.IGNORECASE)

# Drain-pressure policy, mirroring the other governed queues.
# TEAM_TUNABLE_POLICY in thresholds.py.
STALE_OPEN_TELEMETRY_EVIDENCE_DAYS = 30
TELEMETRY_EVIDENCE_QUEUE_DEPTH_NOTE = 10
TELEMETRY_EVIDENCE_PACKAGE_FAIL_TOKENS = 3000

_GATE_ATTESTATION_KEYS = frozenset(GateAttestation.__dataclass_fields__)

# The bounded aggregate shape `hydra.py telemetry report --json` emits.
# Anything else in `metrics.json` is treated as a probable pasted event row
# rather than a derived rollup.
_SCALAR_KEYS = frozenset({
    "generated_at", "window_start", "window_end",
    "event_count", "distinct_event_kinds", "distinct_field_names",
})
_COUNT_MAP_KEYS = frozenset({
    "counts_by_kind", "field_counts", "knowledge_commands", "knowledge_route",
    "reducer_coverage",
})
_LIST_KEYS = frozenset({"event_kinds", "field_names"})
_ALLOWED_METRICS_KEYS = _SCALAR_KEYS | _COUNT_MAP_KEYS | _LIST_KEYS


def _package_dirs(packages_dir: Path) -> list[Path]:
    """Direct subdirectories only. `.gitkeep` and `README.md`-shaped stray
    files are not directories, so they are excluded without a name check."""
    if not packages_dir.is_dir():
        return []
    return sorted(path for path in packages_dir.iterdir() if path.is_dir())


def parse_overview_body(text: str) -> dict:
    """Header fields and section headings from `overview.md`'s body.

    Fields are recognized only above the first `## ` heading, the same rule
    `seed/reflections.py` uses, so a field-shaped line inside `## Findings`
    prose is never mistaken for the header. The YAML envelope above the body
    is scanned too, harmlessly: none of its keys collide with these literal
    `Field:` prefixes.
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
        for field in REQUIRED_HEADER_FIELDS:
            prefix = f"{field}:"
            if stripped.startswith(prefix):
                fields[field] = stripped[len(prefix):].strip()
                break

    sections = {line.strip() for line in lines if line.strip() in REQUIRED_SECTIONS}
    return {"fields": fields, "sections": sections}


def _section_text(text: str, heading: str) -> str:
    lines = text.splitlines()
    start = None
    for index, line in enumerate(lines):
        if line.strip() == heading:
            start = index + 1
            break
    if start is None:
        return ""
    collected: list[str] = []
    for line in lines[start:]:
        if line.strip().startswith("## "):
            break
        collected.append(line)
    return "\n".join(collected)


def _has_event_schema_key(value: Any) -> bool:
    if isinstance(value, dict):
        return "event_schema" in value or any(_has_event_schema_key(v) for v in value.values())
    if isinstance(value, list):
        return any(_has_event_schema_key(item) for item in value)
    return False


def _metrics_shape_findings(metrics: dict, label: str) -> list[Finding]:
    findings: list[Finding] = []

    def add(detail: str) -> None:
        findings.append(Finding(path=label, code=_CODE, detail=detail))

    for key in sorted(set(metrics) - _ALLOWED_METRICS_KEYS):
        add(f"{label}: unknown aggregate bucket `{key}`; metrics.json accepts only {sorted(_ALLOWED_METRICS_KEYS)}")

    for key, value in metrics.items():
        if key in _SCALAR_KEYS:
            if isinstance(value, (dict, list)):
                add(f"{label}: `{key}` must be a scalar, not a {type(value).__name__}")
        elif key in _COUNT_MAP_KEYS:
            if not isinstance(value, dict) or any(not isinstance(v, (int, float)) for v in value.values()):
                add(f"{label}: `{key}` must be a flat map of counts")
        elif key in _LIST_KEYS:
            if not isinstance(value, list) or any(not isinstance(v, str) for v in value):
                add(f"{label}: `{key}` must be a list of strings")
        if isinstance(value, list) and any(isinstance(item, dict) for item in value):
            add(f"{label}: `{key}` holds objects; metrics.json accepts flat maps and lists of strings only, never arrays of objects")

    if _has_event_schema_key(metrics):
        add(f"{label}: `event_schema` key found; metrics.json holds derived aggregates, never raw event rows")

    return findings


def _corpus_mismatch(corpus: str, metrics: dict) -> str | None:
    """Catches the drift class that motivated this check: `overview.md`'s
    `Corpus:` prose hand-copied from a later `telemetry report` run than the
    one that produced this package's own `metrics.json`. Silent otherwise --
    a `Corpus:` not in the template's stated shape is not judged."""
    match = _CORPUS_RE.match(corpus.strip())
    if not match:
        return None
    stated_count = int(match.group(1).replace(",", ""))
    stated_kinds = int(match.group(2))
    actual_count = metrics.get("event_count")
    actual_kinds = metrics.get("distinct_event_kinds")
    if isinstance(actual_count, int) and stated_count != actual_count:
        return (
            f"`Corpus:` states {stated_count} events but metrics.json's `event_count` "
            f"is {actual_count}; regenerate both from the same `telemetry report` run"
        )
    if isinstance(actual_kinds, int) and stated_kinds != actual_kinds:
        return (
            f"`Corpus:` states {stated_kinds} kinds but metrics.json's "
            f"`distinct_event_kinds` is {actual_kinds}; regenerate both from the same "
            "`telemetry report` run"
        )
    return None


def validate_package(
    package_dir: Path,
    root: Path,
    fail_tokens: int = TELEMETRY_EVIDENCE_PACKAGE_FAIL_TOKENS,
    chars_per_token: int = APPROX_CHARS_PER_TOKEN,
) -> list[Finding]:
    findings: list[Finding] = []
    label = display_path(package_dir, root)

    def add(detail: str) -> None:
        findings.append(Finding(path=label, code=_CODE, detail=detail))

    dir_name = package_dir.name
    entries = sorted(path.name for path in package_dir.iterdir())
    for name in entries:
        if (package_dir / name).is_dir():
            add(f"{label}: `{name}` is a subdirectory; packages hold no subdirectories")
        elif name not in REQUIRED_FILES:
            add(f"{label}: unexpected entry `{name}`; a package holds exactly {list(REQUIRED_FILES)}")
    missing_files = [name for name in REQUIRED_FILES if name not in entries]
    for name in missing_files:
        add(f"{label}: missing required file `{name}`")
    if missing_files:
        return findings  # nothing further can be judged without them

    overview_path = package_dir / "overview.md"
    metrics_path = package_dir / "metrics.json"
    attestation_path = package_dir / "gate-attestation.json"
    overview_text = read_text(overview_path)
    metrics_text = read_text(metrics_path)
    attestation_text = read_text(attestation_path)

    for path, text in ((overview_path, overview_text), (metrics_path, metrics_text), (attestation_path, attestation_text)):
        if ".hydra-framework.local/" in text:
            add(f"{display_path(path, root)}: cites a private-tier path; inline what it needs instead")

    date_match = _DIR_NAME_DATE_RE.match(dir_name)
    if not date_match:
        add(f"{label}: directory name must start with `YYYY-MM-DD-`")
    elif _invalid_date(date_match.group(1)):
        add(f"{label}: directory name date `{date_match.group(1)}` is not a valid date")

    try:
        data = markdown_frontmatter(overview_path, root)
    except HydraYamlError as error:
        add(f"{display_path(overview_path, root)}: {error}")
        data = {}

    kind = yaml_str(data.get("kind")).strip().lower()
    hydra_id = yaml_str(data.get("hydra_id")).strip().lower()
    status = yaml_str(data.get("status")).strip().lower()
    superseded_by = yaml_str(data.get("superseded_by")).strip().lower()

    if data and kind and kind != "telemetry-evidence":
        add(f"{display_path(overview_path, root)}: `kind` must be `telemetry-evidence`, got `{kind}`")

    expected_id = f"hydra://telemetry-evidence/{dir_name}"
    if hydra_id and hydra_id != expected_id:
        add(f"{display_path(overview_path, root)}: `hydra_id` must be `{expected_id}`, got `{hydra_id}`")

    if status and status not in TELEMETRY_EVIDENCE_STATUSES:
        add(f"{display_path(overview_path, root)}: `status` must be one of {sorted(TELEMETRY_EVIDENCE_STATUSES)}")

    body = parse_overview_body(overview_text)
    fields = body["fields"]
    for field in REQUIRED_HEADER_FIELDS:
        if not fields.get(field, "").strip():
            add(f"{display_path(overview_path, root)}: missing `{field}:`")
    for heading in REQUIRED_SECTIONS:
        if heading not in body["sections"]:
            add(f"{display_path(overview_path, root)}: missing `{heading}` section")

    author = fields.get("Author", "").strip()
    created = fields.get("Created", "").strip()

    if date_match and created and created != date_match.group(1):
        add(f"{label}: `Created: {created}` does not match directory date `{date_match.group(1)}`")
    if created and _invalid_date(created):
        add(f"{display_path(overview_path, root)}: `Created:` is not a valid `YYYY-MM-DD` date")

    if author and date_match:
        prefix = f"{date_match.group(1)}-{author}-"
        if not dir_name.startswith(prefix):
            add(f"{label}: directory name must be `<Created>-<Author>-<short-slug>` (expected prefix `{prefix}`)")
        else:
            short_slug = dir_name[len(prefix):]
            if not short_slug or not _SHORT_SLUG_RE.match(short_slug):
                add(f"{label}: short-slug segment `{short_slug}` must be non-empty lowercase `a-z0-9-`")

    if status == "superseded" and not superseded_by:
        add(f"{display_path(overview_path, root)}: `status: superseded` requires `superseded_by`")
    if status != "superseded" and superseded_by:
        add(f"{display_path(overview_path, root)}: `superseded_by` is set but status is `{status or 'missing'}`, not `superseded`")
    if status == "absorbed":
        absorption = _section_text(overview_text, "## Absorption").strip()
        if not absorption or absorption.upper().lstrip("<").startswith("TODO"):
            add(f"{display_path(overview_path, root)}: `status: absorbed` requires `## Absorption` to name the artifact it fed")

    try:
        metrics = json.loads(metrics_text)
    except ValueError as error:
        add(f"{display_path(metrics_path, root)}: not valid JSON ({error})")
        metrics = None
    if isinstance(metrics, dict):
        findings.extend(_metrics_shape_findings(metrics, display_path(metrics_path, root)))
        if contains_unsafe_content(metrics):
            add(f"{display_path(metrics_path, root)}: contains unsafe content (absolute path, email, secret- or customer-shaped text)")
        corpus_mismatch = _corpus_mismatch(fields.get("Corpus", ""), metrics)
        if corpus_mismatch:
            add(f"{display_path(overview_path, root)}: {corpus_mismatch}")
    elif metrics is not None:
        add(f"{display_path(metrics_path, root)}: must be a JSON object")

    try:
        attestation = json.loads(attestation_text)
    except ValueError as error:
        add(f"{display_path(attestation_path, root)}: not valid JSON ({error})")
        attestation = None
    if isinstance(attestation, dict):
        missing_keys = sorted(_GATE_ATTESTATION_KEYS - attestation.keys())
        if missing_keys:
            add(f"{display_path(attestation_path, root)}: missing attestation field(s) {missing_keys}")
        if attestation.get("verdict") != "pass":
            add(f"{display_path(attestation_path, root)}: attestation verdict is `{attestation.get('verdict')}`, not `pass`; a failing attestation is not evidence")
    elif attestation is not None:
        add(f"{display_path(attestation_path, root)}: must be a JSON object")

    if contains_unsafe_content(overview_text):
        add(f"{display_path(overview_path, root)}: contains unsafe content (absolute path, email, secret- or customer-shaped text)")

    combined_tokens = approx_tokens(overview_text + metrics_text + attestation_text, chars_per_token)
    if combined_tokens > fail_tokens:
        add(f"{label}: {combined_tokens} approx tokens exceeds the {fail_tokens}-token package ceiling")

    return findings


def _invalid_date(value: str) -> bool:
    try:
        date.fromisoformat(value)
    except ValueError:
        return True
    return False


def validate_telemetry_evidence_queue(packages_dir: Path, root: Path) -> list[Finding]:
    """Enforce package shape. An absent directory is valid: nothing filed yet."""
    findings: list[Finding] = []
    for package_dir in _package_dirs(packages_dir):
        findings.extend(validate_package(package_dir, root))
    return findings


def telemetry_evidence_notes(
    packages_dir: Path,
    root: Path,
    hydra: Path,
    today: str,
    stale_days: int = STALE_OPEN_TELEMETRY_EVIDENCE_DAYS,
    depth_note: int = TELEMETRY_EVIDENCE_QUEUE_DEPTH_NOTE,
) -> list[str]:
    """Advisory drain-pressure signals, never build failures (placement rules):
    an aging `open` package, queue depth, and an attestation that predates
    the current redaction contract. Only `open` packages are checked; a
    terminal status already answered the question a note would raise."""
    notes: list[str] = []
    today_date = date.fromisoformat(today)
    stale_cutoff = today_date - timedelta(days=stale_days)
    current_digest: str | None = None  # computed lazily: only open packages need it
    open_count = 0

    for package_dir in _package_dirs(packages_dir):
        overview = package_dir / "overview.md"
        if not overview.exists():
            continue
        try:
            data = markdown_frontmatter(overview, root)
        except HydraYamlError:
            continue
        if yaml_str(data.get("status")).strip().lower() not in NON_TERMINAL_TELEMETRY_EVIDENCE_STATUSES:
            continue
        open_count += 1
        label = display_path(package_dir, root)

        fields = parse_overview_body(read_text(overview)).get("fields", {})
        created = fields.get("Created", "").strip()
        try:
            if created and date.fromisoformat(created) < stale_cutoff:
                notes.append(f"{label}: open telemetry evidence package filed {created}, past the {stale_days}-day drain expectation")
        except ValueError:
            pass  # malformed date is already a `validate_package` error

        attestation_path = package_dir / "gate-attestation.json"
        if attestation_path.exists():
            try:
                attestation = json.loads(read_text(attestation_path))
            except ValueError:
                attestation = None
            if isinstance(attestation, dict) and attestation.get("redaction_digest") is not None:
                if current_digest is None:
                    current_digest = redaction_digest(hydra)
                if attestation["redaction_digest"] != current_digest:
                    notes.append(f"{label}: gate-attestation.json predates the current redaction contract; re-run `hydra.py telemetry gate`")

    if open_count > depth_note:
        notes.append(f"repo/telemetry/packages/: {open_count} open packages, above the {depth_note}-package readability backstop")
    return notes
