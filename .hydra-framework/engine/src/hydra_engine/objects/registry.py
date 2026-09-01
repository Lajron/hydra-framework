"""Derived object registry text and freshness.

Every message this function produces already opens with `registry_display`
(the registry file itself is always the subject: "the registry says X about
`id`, which is stale"), so `path=registry_display` is used for every finding
here rather than trying to separately attribute each one to the object it
describes -- the message's own leading text already names that object where
relevant, and the registry file is genuinely what a reader would need to
open to act on any of them.
"""

from __future__ import annotations

from pathlib import Path

from hydra_engine.documents.tokens import display_path, read_text, write_text, yaml_scalar
from hydra_engine.documents.yaml_documents import yaml_list, yaml_quote, yaml_str
from hydra_engine.finding import Finding
from hydra_engine.objects.discovery import collect_hydra_objects
from hydra_engine.objects.moves import AMBIGUOUS_MOVE, MoveVerdict, detect_object_moves, path_exists_from_registry
from hydra_engine.objects.references import validate_object_references

_CODE = "object-registry-freshness"


def object_registry_text(objects: list[dict]) -> str:
    lines = [
        "schema: hydra-framework.object-registry.v1",
        "objects:",
    ]
    for obj in sorted(objects, key=lambda item: item["id"]):
        lines.append(f"  {obj['id']}:")
        # Objects below UID_REQUIRED_FROM_SCHEMA_VERSION may legitimately have
        # no uid yet. Omitting the line records "unrecorded" rather than
        # exporting an empty value that reads like a real identity.
        if obj["uid"]:
            lines.append(f"    uid: {obj['uid']}")
        lines.extend([
            f"    path: {obj['path']}",
            f"    digest: {obj['digest']}",
            f"    family: {obj['family']}",
            f"    kind: {obj['kind']}",
            f"    status: {obj['status']}",
            f"    tier: {obj['tier']}",
            f"    scope: {obj['scope']}",
            f"    schema_version: {obj['schema_version']}",
            f"    title: {yaml_quote(obj['title'])}",
        ])
        aliases = obj["aliases"]
        if aliases:
            lines.append("    aliases:")
            lines.extend(f"      - {alias}" for alias in aliases)
        else:
            lines.append("    aliases: []")
        if obj["envelope_path"] != obj["path"]:
            lines.append(f"    envelope_path: {obj['envelope_path']}")
        relations = obj["relations"]
        if relations:
            lines.append("    relations:")
            lines.extend(f"      - {relation}" for relation in relations)
        else:
            lines.append("    relations: []")
        sources = obj["provenance_sources"]
        if sources:
            lines.append("    provenance_sources:")
            lines.extend(f"      - {source}" for source in sources)
        else:
            lines.append("    provenance_sources: []")
    return "\n".join(lines) + "\n"


def registry_object_entries(path: Path, root: Path) -> tuple[dict[str, dict[str, object]], list[str]]:
    """Read the generated object registry format without treating it as source YAML."""
    if not path.exists():
        return {}, []

    entries: dict[str, dict[str, object]] = {}
    errors: list[str] = []
    current: str | None = None
    current_list: str | None = None
    schema_seen = False

    for raw in read_text(path).splitlines():
        stripped = raw.strip()
        if stripped == "schema: hydra-framework.object-registry.v1":
            schema_seen = True
            continue
        if raw.startswith("  hydra://") and stripped.endswith(":"):
            current = stripped[:-1].lower()
            entries.setdefault(current, {"aliases": []})
            current_list = None
            continue
        if current is None:
            continue
        if raw.startswith("    ") and not raw.startswith("      "):
            key, separator, value = stripped.partition(":")
            if not separator:
                errors.append(f"{display_path(path, root)} has malformed registry line `{stripped}`")
                continue
            if value.strip():
                stripped_value = value.strip()
                if stripped_value in {"[]", "{}"}:
                    entries[current][key] = [] if stripped_value == "[]" else {}
                else:
                    entries[current][key] = yaml_scalar(stripped_value)
                current_list = None
            else:
                entries[current][key] = []
                current_list = key
            continue
        if raw.startswith("      - ") and current_list:
            values = entries[current].setdefault(current_list, [])
            if isinstance(values, list):
                values.append(stripped[2:].strip())

    if not schema_seen:
        errors.append(f"{display_path(path, root)} is not a Hydra object registry")
    return entries, errors


def validate_object_registry_freshness(
    paths: ObjectLocations,
    *,
    objects_result: tuple[list[dict], list[str]] | None = None,
) -> list[Finding]:
    """Verify the derived registry still reflects canonical object metadata.

    `objects_result` lets a caller that already ran `collect_hydra_objects` on
    this exact `paths` pass the result through instead of re-scanning.
    Omit it to scan as before."""
    if not paths.object_registry.exists():
        return []

    objects, object_errors = objects_result if objects_result is not None else collect_hydra_objects(paths)
    if object_errors:
        return []

    registry, registry_errors = registry_object_entries(paths.object_registry, paths.root)
    if registry_errors:
        return [Finding(path=display_path(paths.object_registry, paths.root), code=_CODE, detail=error) for error in registry_errors]

    findings: list[Finding] = []
    current_by_id = {obj["id"]: obj for obj in objects}
    registry_display = display_path(paths.object_registry, paths.root)
    moves = {move.recorded_id: move for move in detect_object_moves(registry, objects, paths)}

    def _finding(detail: str) -> Finding:
        return Finding(path=registry_display, code=_CODE, detail=detail)

    for hydra_id, entry in sorted(registry.items()):
        stored_path = yaml_str(entry.get("path"))
        stored_digest = yaml_str(entry.get("digest"))
        stored_uid = yaml_str(entry.get("uid"))
        if stored_path and not path_exists_from_registry(stored_path, paths):
            findings.append(_finding(f"{registry_display} has missing path for `{hydra_id}`: {stored_path}"))

        move = moves.get(hydra_id)
        current = current_by_id.get(hydra_id)
        if not current:
            if move and move.verdict.is_unambiguous:
                findings.append(_finding(
                    f"{registry_display} has stale object `{hydra_id}` at {stored_path}; "
                    f"unambiguous move to `{move.current_id}` at {move.to_path} "
                    f"({move.verdict.detail()}); rerun `hydra.py ref index`"
                ))
            elif move and move.verdict.classification == AMBIGUOUS_MOVE:
                findings.append(_finding(
                    f"{registry_display} has stale object `{hydra_id}` at {stored_path}; "
                    f"possible move to {move.to_path} is ambiguous ({move.verdict.detail()}); "
                    f"decide this by hand"
                ))
            else:
                findings.append(_finding(f"{registry_display} has stale object `{hydra_id}`"))
            continue

        if stored_path != current["path"]:
            verdict = move.verdict if move else MoveVerdict(AMBIGUOUS_MOVE, "unknown-identity")
            if verdict.is_unambiguous:
                findings.append(_finding(
                    f"{registry_display} has stale path for `{hydra_id}`: "
                    f"{stored_path} -> {current['path']} (unambiguous move: {verdict.detail()}); "
                    f"rerun `hydra.py ref index`"
                ))
            else:
                label = "ambiguous" if verdict.classification == AMBIGUOUS_MOVE else "not a move"
                findings.append(_finding(
                    f"{registry_display} has stale path for `{hydra_id}`: "
                    f"{stored_path} -> {current['path']} ({label}: {verdict.detail()}); "
                    f"decide this by hand"
                ))
        if stored_digest != current["digest"]:
            findings.append(_finding(
                f"{registry_display} has stale digest for `{hydra_id}`; rerun `hydra.py ref index`"
            ))
        # A registry written before uid was exported is silent about uid, not
        # wrong about it, so only a recorded-and-different uid is stale.
        if stored_uid and stored_uid != current["uid"]:
            findings.append(_finding(
                f"{registry_display} has stale uid for `{hydra_id}`; rerun `hydra.py ref index`"
            ))

        stored_aliases = sorted(yaml_list(entry.get("aliases")))
        if stored_aliases != current["aliases"]:
            findings.append(_finding(
                f"{registry_display} has stale aliases for `{hydra_id}`; rerun `hydra.py ref index`"
            ))

    for hydra_id in sorted(set(current_by_id) - set(registry)):
        findings.append(_finding(f"{registry_display} is missing object `{hydra_id}`"))

    return findings


def scan_objects(paths: ObjectLocations) -> tuple[list[dict], list[str]]:
    """`collect_hydra_objects`, exposed here for callers that need the full
    scanned object graph but not registry writing (`explain-path`).
    `objects.discovery` already sits at architecture check 4's
    in-degree cap (ten direct importers, each already required to reach it
    for their own reason), so a new caller reuses this module's existing
    import instead of adding an eleventh edge onto a module the check
    requires to stay a leaf past that threshold."""
    return collect_hydra_objects(paths)


def validate_object_model(paths: ObjectLocations) -> list[Finding]:
    """`validate_object_references` then, if that is clean,
    `validate_object_registry_freshness` -- the pair every caller that wants
    a full object-model verdict already runs back to back. Sharing one
    `collect_hydra_objects` scan between them is the whole point:
    two full-tree scans collapse into one."""
    objects_result = collect_hydra_objects(paths)
    findings = validate_object_references(paths, objects_result=objects_result)
    if findings:
        return findings
    return findings + validate_object_registry_freshness(paths, objects_result=objects_result)


def write_object_registry(paths: ObjectLocations) -> int | None:
    """Rewrite the derived registry from current canonical metadata.

    Owned here rather than by either command that calls it (`ref index`,
    `move-object`) so those two `commands/` modules never need to import
    each other for it.

    Returns `None`, leaving any existing registry untouched, if discovery
    reports errors -- writing whatever partial object list came back would
    corrupt the registry. Both callers already validate before reaching
    here, so this only fires on a race between that check and this scan
    (for example a concurrent atomic replace mid-scan).
    """
    objects, errors = collect_hydra_objects(paths)
    if errors:
        return None
    write_text(paths.object_registry, object_registry_text(objects))
    return len(objects)
