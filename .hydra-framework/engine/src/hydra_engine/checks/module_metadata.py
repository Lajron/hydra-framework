"""Canonical module metadata.

Every canonical module needs the metadata its exporters depend on. Moved
here unchanged from `scripts/hydra.py`'s `validate_module_metadata` (it was
never a delegator -- this is the first time its body has lived in the
engine) and converted to return `Finding` per Target Structure rule 2; every
`detail` string below is byte-identical to the message the old `list[str]`
entry held.

Takes already-discovered, already-parsed `ModuleMetadataEntry` values
rather than globbing `hydra`'s module directories and calling
`documents.yaml_documents.parse_yaml` itself: `documents.yaml_documents` is
already at exactly in-degree 10, the check-4 cap -- becoming an 11th
importer here would trip it again. `scripts/hydra.py`'s wrapper does the globbing and parsing (it
already imports `yaml_documents` for real, at no incremental in-degree
cost) and passes the result down as plain data; this module reimplements
`yaml_str`'s one-line semantics locally rather than importing it for that
alone.
"""

from __future__ import annotations

import dataclasses
from pathlib import Path

from hydra_engine.documents.tokens import display_path
from hydra_engine.finding import Finding

MODULE_METADATA_CHECKS = [
    ("capabilities/skills", "skill.md", ["name", "description"]),
    ("capabilities/agents", "agent.md", ["name", "description", "capability_class", "effort"]),
]


@dataclasses.dataclass(frozen=True)
class ModuleMetadataEntry:
    module_dir: Path
    metadata_path: Path
    required: list[str]
    is_skill: bool
    data: dict | None
    parse_error: str | None


def _yaml_str(value: object, fallback: str = "") -> str:
    return value if isinstance(value, str) else fallback


def validate_module_metadata(entries: list[ModuleMetadataEntry], root: Path) -> list[Finding]:
    findings: list[Finding] = []
    for entry in entries:
        if entry.parse_error is not None:
            path = display_path(entry.metadata_path, root)
            findings.append(Finding(path=path, code="module-metadata", detail=entry.parse_error))
            continue
        if entry.data is None:
            path = display_path(entry.module_dir, root)
            findings.append(Finding(path=path, code="module-metadata", detail=f"{path} missing metadata.yaml"))
            continue

        path = display_path(entry.metadata_path, root)
        for key in entry.required:
            if not _yaml_str(entry.data.get(key)):
                findings.append(Finding(path=path, code="module-metadata", detail=f"{path} missing `{key}`"))
        kind = _yaml_str(entry.data.get("kind"), "procedure")
        if entry.is_skill and kind not in {"procedure", "command"}:
            findings.append(Finding(
                path=path, code="module-metadata",
                detail=f"{path} `kind` must be `procedure` or `command`, got `{kind}`",
            ))
    return findings
