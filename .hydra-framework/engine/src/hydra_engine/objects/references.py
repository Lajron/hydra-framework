"""Cross-object reference validation.

`code` is `"object-references"` for every finding this module produces --
one per producing function, not per message shape, matching every other
`validate_*` conversion. `path` is the single object path a message is
about when there is exactly one; a message that names several objects at
once (a duplicate id/uid/reference spanning multiple files) gets `path=""`
rather than an invented "first" path, per `Finding`'s own "spans more than
one thing" rule. The leading `collect_hydra_objects` errors are opaque
strings from a function that stays `list[str]` (it is not itself
`validate_*`-named) and are wrapped with `path=""` rather than parsed for a
path, since parsing prose to recover structure `Finding` was designed to
avoid inventing is not a real improvement.
"""

from __future__ import annotations

from hydra_engine.documents.tokens import cited_source_path_missing, display_path, read_text
from hydra_engine.finding import Finding
from hydra_engine.identity.hydra_ids import hydra_refs_in_text
from hydra_engine.identity.schema_versions import (
    EMPTY_ALLOWED_ENVELOPE_FIELDS,
    ENVELOPE_REQUIRED_FROM_SCHEMA_VERSION,
    UID_REQUIRED_FROM_SCHEMA_VERSION,
)
from hydra_engine.objects.discovery import collect_hydra_objects, object_metadata_paths
from hydra_engine.objects.envelopes import resolved_envelope_path

_CODE = "object-references"


def validate_object_references(
    paths: ObjectLocations,
    *,
    objects_result: tuple[list[dict], list[str]] | None = None,
) -> list[Finding]:
    """`objects_result` lets a caller that already ran `collect_hydra_objects`
    on this exact `paths` pass the result through instead of re-scanning the
    tree. Omit it to scan as before."""
    objects, discovery_errors = objects_result if objects_result is not None else collect_hydra_objects(paths)
    findings = [Finding(path="", code=_CODE, detail=error) for error in discovery_errors]

    by_id: dict[str, list[dict]] = {}
    for obj in objects:
        by_id.setdefault(obj["id"], []).append(obj)

    for hydra_id, matches in sorted(by_id.items()):
        if len(matches) > 1:
            object_paths = ", ".join(match["path"] for match in matches)
            findings.append(Finding(path="", code=_CODE, detail=f"duplicate hydra_id `{hydra_id}` in {object_paths}"))

    by_uid: dict[str, list[dict]] = {}
    for obj in objects:
        if obj["uid"]:
            by_uid.setdefault(obj["uid"], []).append(obj)
        elif obj["schema_version"] >= UID_REQUIRED_FROM_SCHEMA_VERSION:
            findings.append(Finding(path=obj["path"], code=_CODE, detail=f"{obj['path']} is missing required uid"))

    for uid, matches in sorted(by_uid.items()):
        if len(matches) > 1:
            object_paths = ", ".join(match["path"] for match in matches)
            findings.append(Finding(path="", code=_CODE, detail=f"duplicate uid `{uid}` in {object_paths}"))

    for obj in objects:
        if obj["schema_version"] < ENVELOPE_REQUIRED_FROM_SCHEMA_VERSION:
            continue
        for field in obj["missing_envelope_fields"]:
            if field in EMPTY_ALLOWED_ENVELOPE_FIELDS:
                # Say so explicitly. An agent told only that a field is missing
                # will reach for something to put in it, which is the outcome
                # keeping this slot empty-able is meant to prevent.
                findings.append(Finding(
                    path=obj["path"], code=_CODE,
                    detail=(
                        f"{obj['path']} is missing required {field}; "
                        f"an empty list is the right answer when there is nothing real to name"
                    ),
                ))
            else:
                findings.append(Finding(path=obj["path"], code=_CODE, detail=f"{obj['path']} is missing required {field}"))
        # Same gate, same reason (the object-family registry): below
        # this version `kind` is not yet a required field, so judging the value
        # of a field the object was never obliged to declare would be
        # incoherent. An unregistered family is a divergence someone has to
        # either declare or fix, which is why it names the registry outright.
        for token in obj["unregistered_family_tokens"]:
            findings.append(Finding(
                path=obj["path"], code=_CODE,
                detail=(
                    f"{obj['path']} has unregistered {token}; register the family in "
                    f"hydra_engine.identity.object_families or correct the value"
                ),
            ))

    for obj in objects:
        citation_dir = resolved_envelope_path(obj["envelope_path"], paths).parent
        for raw in obj["provenance_sources"]:
            if cited_source_path_missing(raw, citation_dir, paths.root):
                findings.append(Finding(
                    path=obj["envelope_path"], code=_CODE,
                    detail=f"{obj['envelope_path']}: `provenance.sources` path does not exist: {raw}",
                ))

    by_ref: dict[str, list[dict]] = {}
    for obj in objects:
        identifiers = [obj["id"], *obj["aliases"]]
        if len(identifiers) != len(set(identifiers)):
            findings.append(Finding(
                path=obj["path"], code=_CODE,
                detail=f"{obj['path']} repeats primary hydra_id as an alias `{obj['id']}`",
            ))
        for ref in set(identifiers):
            by_ref.setdefault(ref, []).append(obj)

    for ref, matches in sorted(by_ref.items()):
        unique_ids = sorted({match["id"] for match in matches})
        if len(unique_ids) > 1:
            object_paths = ", ".join(match["path"] for match in matches)
            findings.append(Finding(path="", code=_CODE, detail=f"duplicate hydra reference `{ref}` in {object_paths}"))

    known = set(by_ref)
    for path in object_metadata_paths(paths):
        try:
            refs = hydra_refs_in_text(path, read_text(path))
        except OSError as error:
            findings.append(Finding(
                path=display_path(path, paths.root), code=_CODE,
                detail=f"{display_path(path, paths.root)}: {error}",
            ))
            continue
        for ref in refs:
            if ref not in known:
                findings.append(Finding(
                    path=display_path(path, paths.root), code=_CODE,
                    detail=f"{display_path(path, paths.root)} references unresolved `{ref}`",
                ))
    return findings
