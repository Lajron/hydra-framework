"""schema command decisions: schema upgrade.

`resolver_paths: ObjectLocations` is a bare forward-reference type hint (no
real import), matching the established codebase-wide convention.
"""

from __future__ import annotations

import sys
from pathlib import Path

from hydra_engine.commands import CommandResult
from hydra_engine.documents.tokens import read_text, write_text
from hydra_engine.identity.schema_versions import CURRENT_SCHEMA_VERSION, ENVELOPE_REQUIRED_FROM_SCHEMA_VERSION
from hydra_engine.objects import schema_upgrades as migrations_engine
from hydra_engine.objects.discovery import collect_hydra_objects
from hydra_engine.objects.envelopes import resolved_envelope_path


def command_schema_upgrade(_args, resolver_paths) -> CommandResult:
    """Upgrade every canonical object's envelope to the current schema_version.

    Named, idempotent, re-runnable: an object already at
    `CURRENT_SCHEMA_VERSION` is left untouched, so running this twice in a
    row - or running it in a downstream copy that already upgraded - changes
    nothing the second time.
    """
    objects, errors = collect_hydra_objects(resolver_paths)
    if errors:
        print("Hydra schema upgrade: failed", file=sys.stderr)
        for error in errors:
            print(f"- {error}", file=sys.stderr)
        return CommandResult(1)

    by_file: dict[Path, list[dict]] = {}
    for obj in objects:
        by_file.setdefault(resolved_envelope_path(obj["envelope_path"], resolver_paths), []).append(obj)

    upgraded: list[str] = []
    for path, file_objects in sorted(by_file.items()):
        text = read_text(path)
        applied_for_file: list[str] = []
        for obj in file_objects:
            text, applied = migrations_engine.upgrade_envelope_text(text, obj["id"], obj["schema_version"])
            if applied:
                applied_for_file.append(obj["id"])
        if applied_for_file:
            write_text(path, text)
            upgraded.extend(applied_for_file)

    print(
        f"Hydra schema upgrade: {len(upgraded)} of {len(objects)} objects upgraded "
        f"to schema_version {CURRENT_SCHEMA_VERSION}"
    )
    for hydra_id in upgraded:
        print(f"- {hydra_id}")
    if not upgraded:
        print("Nothing to upgrade; every object is already at the current schema_version.")
        return CommandResult(0)

    # Say now what validation would otherwise say later. A migration writes only
    # the envelope fields whose empty value is a real answer; the rest have to be
    # authored, and naming them here turns a surprise `validate` failure into a
    # list of work this command just created.
    upgraded_objects, _ = collect_hydra_objects(resolver_paths)
    owed = [
        obj
        for obj in upgraded_objects
        if obj["schema_version"] >= ENVELOPE_REQUIRED_FROM_SCHEMA_VERSION
        and obj["missing_envelope_fields"]
    ]
    if owed:
        print("\nThese objects now need envelope fields no migration may write for them:")
        for obj in owed:
            print(f"- {obj['path']}: {', '.join(obj['missing_envelope_fields'])}")
    return CommandResult(0)


def register(subparsers) -> None:
    """Add `schema upgrade`."""
    schema = subparsers.add_parser("schema", help="Manage the Hydra object envelope schema version")
    schema_sub = schema.add_subparsers(dest="schema_command", required=True)
    schema_sub.add_parser(
        "upgrade", help="Upgrade every canonical object's envelope to the current schema_version"
    ).set_defaults(func=_dispatch_schema_upgrade)


def _dispatch_schema_upgrade(args, ctx) -> int:
    return command_schema_upgrade(args, ctx.resolver_paths()).exit_code
