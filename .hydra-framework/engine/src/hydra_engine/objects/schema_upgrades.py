"""Envelope schema migrations.

Every change to the object envelope ships its own upgrade step: named,
idempotent, and re-runnable. Idempotent means an object already at
`CURRENT_SCHEMA_VERSION` is returned unchanged; re-runnable means running the
same step twice, or across a downstream copy that already applied it, is
defined behavior rather than an accident.

This module only computes text. It reads nothing and writes nothing -
`hydra.py schema upgrade` owns reading each envelope file, applying
`upgrade_envelope_text`, and writing back only what changed, the same split
the object model uses for registry text versus registry files.
"""

from __future__ import annotations

from dataclasses import dataclass

from hydra_engine.identity.schema_versions import CURRENT_SCHEMA_VERSION, UNVERSIONED_SCHEMA_VERSION
from hydra_engine.objects.envelopes import envelope_block_end, envelope_field_line_index
from hydra_engine.ports import uids as uids_port

# Each migration upgrades to a fixed version, pinned here rather than read from
# CURRENT_SCHEMA_VERSION, so adding a later migration never changes what an
# earlier step meant.
_SCHEMA_VERSION_1 = 1
_SCHEMA_VERSION_2 = 2


@dataclass(frozen=True)
class EnvelopeMigration:
    name: str
    from_version: int
    to_version: int
    description: str


def _field_index_in_block(lines: list[str], start: int, end: int, indent: int, field: str) -> int | None:
    """Index of `field` at exactly `indent` within [start, end), else None.

    Indent-sensitive on purpose: `sources` under `provenance` must not be
    mistaken for an envelope-level field, and vice versa.
    """
    prefix = f"{field}:"
    for index in range(start, end):
        line = lines[index]
        if len(line) - len(line.lstrip(" ")) != indent:
            continue
        if line.strip().lower().startswith(prefix):
            return index
    return None


def _introduce_schema_version(text: str, hydra_id: str, to_version: int) -> tuple[str, bool]:
    """v0 -> v1: add the `schema_version` field next to `hydra_id`.

    Scoped to the one object envelope named `hydra_id` within `text`, so a
    sidecar file holding many objects only gets one insertion per call.
    """
    lines = text.splitlines()
    anchor = envelope_field_line_index(lines, "hydra_id", hydra_id)
    if anchor is None:
        return text, False
    indent = len(lines[anchor]) - len(lines[anchor].lstrip(" "))
    end = envelope_block_end(lines, anchor, indent)
    if _field_index_in_block(lines, anchor, end, indent, "schema_version") is not None:
        return text, False
    lines.insert(anchor + 1, " " * indent + f"schema_version: {to_version}")
    newline = "\n" if text.endswith("\n") else ""
    return "\n".join(lines) + newline, True


def _backfill_uid(text: str, hydra_id: str, to_version: int) -> tuple[str, bool]:
    """v1 -> v2: add the opaque `uid` field and bump `schema_version`.

    Scoped to the one object envelope named `hydra_id`, mirroring
    `_introduce_schema_version`. `uid` is a UUID4, generated fresh only when
    the object does not already carry one, so an object already migrated -
    including by a downstream copy that backfilled independently - is left
    untouched rather than reassigned a new identity.
    """
    lines = text.splitlines()
    anchor = envelope_field_line_index(lines, "hydra_id", hydra_id)
    if anchor is None:
        return text, False
    indent = len(lines[anchor]) - len(lines[anchor].lstrip(" "))
    end = envelope_block_end(lines, anchor, indent)

    has_uid = _field_index_in_block(lines, anchor, end, indent, "uid") is not None
    version_index = _field_index_in_block(lines, anchor, end, indent, "schema_version")
    # An object that already carries a uid but is still recorded below this
    # version - a downstream copy that backfilled uid by hand, say - still
    # needs the version raised, or it would sit below every later migration
    # forever. Only an object that is done on both counts is a no-op.
    if has_uid and version_index is not None and lines[version_index].strip() == f"schema_version: {to_version}":
        return text, False

    if version_index is not None:
        lines[version_index] = " " * indent + f"schema_version: {to_version}"
    if not has_uid:
        lines.insert(anchor + 1, " " * indent + f"uid: {uids_port.new_uid()}")
    newline = "\n" if text.endswith("\n") else ""
    return "\n".join(lines) + newline, True


def _backfill_empty_envelope_slots(text: str, hydra_id: str, to_version: int) -> tuple[str, bool]:
    """v2 -> v3: add the `relations` and `provenance.sources` slots, empty.

    These two are the only mandatory envelope fields a migration may write,
    and the reason is the same one that lets them be empty: an empty slot
    there is a real answer, so writing `[]` states something true rather than
    inventing a relationship or a source.
    The other five - kind, title, status, scope, owners - are deliberately not
    backfilled. There is no value for them that would be true without an author,
    so an object missing one is upgraded anyway and reported by validation,
    which is the honest outcome.

    Existing content is never touched: an object that already declares
    `relations` or `provenance.sources`, empty or not, keeps exactly what it has
    and only has its `schema_version` raised.
    """
    lines = text.splitlines()
    anchor = envelope_field_line_index(lines, "hydra_id", hydra_id)
    if anchor is None:
        return text, False
    indent = len(lines[anchor]) - len(lines[anchor].lstrip(" "))
    end = envelope_block_end(lines, anchor, indent)

    version_index = _field_index_in_block(lines, anchor, end, indent, "schema_version")
    if version_index is None:
        return text, False
    lines[version_index] = " " * indent + f"schema_version: {to_version}"

    additions: list[str] = []
    if _field_index_in_block(lines, anchor, end, indent, "relations") is None:
        additions.append(" " * indent + "relations: []")

    provenance_index = _field_index_in_block(lines, anchor, end, indent, "provenance")
    if provenance_index is None:
        additions.extend([" " * indent + "provenance:", " " * (indent + 2) + "sources: []"])
    else:
        inline = lines[provenance_index].partition(":")[2].strip()
        provenance_end = min(envelope_block_end(lines, provenance_index, indent + 2), end)
        has_sources = _field_index_in_block(lines, provenance_index + 1, provenance_end, indent + 2, "sources")
        if inline:
            # `provenance: {}` says "no sources" inline; reopen it as a block so
            # the slot can be written where the envelope expects to read it.
            lines[provenance_index] = " " * indent + "provenance:"
        if inline or has_sources is None:
            lines.insert(provenance_index + 1, " " * (indent + 2) + "sources: []")
            end += 1

    for offset, line in enumerate(additions):
        lines.insert(end + offset, line)

    newline = "\n" if text.endswith("\n") else ""
    return "\n".join(lines) + newline, True


MIGRATIONS: list[EnvelopeMigration] = [
    EnvelopeMigration(
        name="introduce-schema-version",
        from_version=UNVERSIONED_SCHEMA_VERSION,
        to_version=_SCHEMA_VERSION_1,
        description="Add the schema_version envelope field.",
    ),
    EnvelopeMigration(
        name="backfill-uid",
        from_version=_SCHEMA_VERSION_1,
        to_version=_SCHEMA_VERSION_2,
        description="Add the opaque uid envelope field.",
    ),
    EnvelopeMigration(
        name="backfill-empty-envelope-slots",
        from_version=_SCHEMA_VERSION_2,
        to_version=CURRENT_SCHEMA_VERSION,
        description="Add the empty relations and provenance.sources slots.",
    ),
]

_STEP_APPLIERS = {
    "introduce-schema-version": _introduce_schema_version,
    "backfill-uid": _backfill_uid,
    "backfill-empty-envelope-slots": _backfill_empty_envelope_slots,
}


def upgrade_envelope_text(text: str, hydra_id: str, current_version: int) -> tuple[str, list[str]]:
    """Apply every migration step this object still needs, in order.

    Returns the (possibly unchanged) text and the names of steps actually
    applied. An object already at `CURRENT_SCHEMA_VERSION` gets back the same
    text and an empty list - this is the idempotency contract. An object
    starting below `CURRENT_SCHEMA_VERSION` by more than one step chains
    through every migration it still needs in a single call.
    """
    applied: list[str] = []
    version = current_version
    for migration in MIGRATIONS:
        if version != migration.from_version:
            continue
        text, changed = _STEP_APPLIERS[migration.name](text, hydra_id, migration.to_version)
        if changed:
            applied.append(migration.name)
            version = migration.to_version
    return text, applied
