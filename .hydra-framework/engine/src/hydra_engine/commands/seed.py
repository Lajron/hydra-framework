"""seed command decisions: diff-base,
evolution record.

`manifest` is the already-parsed `manifest.yaml` dict, computed once by
`hydra.py`'s thin wrapper and passed down, matching `commands.installation`'s
`command_adopt` shape: this module never imports `documents.yaml_documents`
itself (that module is already at check 4's in-degree cap of 10). Its two trivial
value-coercion needs (`yaml_map`/`yaml_str`'s shape) are reimplemented
locally rather than pulled in for that alone, matching
`hydra_engine.installation.adopt`'s and `hydra_engine.seed.adaptations`'
precedent. `resolver_paths: ObjectLocations` is a bare forward-reference type
hint here (no real import): this module only passes an already-constructed
instance through to `envelope_schema_drift`, matching the established
codebase-wide convention for this exact shape.
"""

from __future__ import annotations

import datetime as _dt
import json
import sys
from pathlib import Path

from hydra_engine.commands import CommandResult
from hydra_engine.documents.tokens import display_path, read_text
from hydra_engine.ports import clock
from hydra_engine.seed.adaptations import (
    ADAPTATION_DISPOSITIONS,
    append_adaptation_entry,
    current_base_seed_version,
    format_adaptation_entry,
    parse_adaptation_ledger_text,
    validate_adaptation_entries,
)
from hydra_engine.seed.comparison import split_differences_by_adaptation
from hydra_engine.seed.envelope_drift import envelope_schema_drift
from hydra_engine.seed.fingerprints import iter_framework_files


def _as_map(value: object) -> dict:
    return value if isinstance(value, dict) else {}


def _as_str(value: object, fallback: str = "") -> str:
    return value if isinstance(value, str) else fallback


def command_diff_base(args, paths, resolver_paths: ObjectLocations, manifest: dict) -> CommandResult:
    """Classify this repository's Hydra copy against the base seed it came from."""
    base_root = Path(args.base).expanduser().resolve()
    base_hydra = base_root / ".hydra-framework" if base_root.name != ".hydra-framework" else base_root
    if not base_hydra.is_dir():
        print(f"Hydra diff-base: no framework at {base_hydra}", file=sys.stderr)
        return CommandResult(1)
    if base_hydra.resolve() == paths.hydra.resolve():
        print("Hydra diff-base: base and local are the same directory", file=sys.stderr)
        return CommandResult(1)

    local = iter_framework_files(paths.hydra)
    base = iter_framework_files(base_hydra)

    identical = sorted(path for path in local if path in base and local[path] == base[path])
    modified = sorted(path for path in local if path in base and local[path] != base[path])
    local_only = sorted(path for path in local if path not in base)
    base_only = sorted(path for path in base if path not in local)

    lineage = _as_map(manifest.get("lineage"))
    rows = {
        "identical": identical,
        "local-modified": modified,
        "local-only": local_only,
        "base-only": base_only,
    }
    ledger_entries = (
        parse_adaptation_ledger_text(read_text(paths.adaptation_ledger))
        if paths.adaptation_ledger.exists()
        else []
    )
    schema_drift = envelope_schema_drift(resolver_paths, base_hydra)
    split = split_differences_by_adaptation(rows, ledger_entries, schema_drift)

    if args.json:
        print(json.dumps({
            "base": str(base_hydra),
            "local_seed_version": _as_str(manifest.get("seed_version")),
            "lineage": lineage,
            "counts": {
                "explained": len(split["explained"]),
                "unexplained": len(split["unexplained"]),
                "identical": len(identical),
            },
            "mechanical_counts": {key: len(value) for key, value in rows.items()},
            "differences": split,
        }, indent=2))
    else:
        print(f"Hydra seed comparison against {base_hydra}")
        print(f"Local seed version: {_as_str(manifest.get('seed_version'), 'unknown')}")
        if lineage:
            print(f"Lineage: {json.dumps(lineage, sort_keys=True)}")
        else:
            print("Lineage: not recorded (run `hydra.py adopt --record`); classification is less reliable")
        print("")
        print(f"explained differences: {len(split['explained'])}")
        for item in split["explained"]:
            print(f"- {item['path']} ({item['mechanical']}): {', '.join(item['explained_by'])}")
        print(f"unexplained differences: {len(split['unexplained'])}")
        for item in split["unexplained"]:
            print(f"- {item['path']} ({item['mechanical']})")
        print(f"identical: {len(identical)}")
        print("")
        print("Next: classify unexplained differences by intent before reconciling.")
        print("Use the `hydra-seed-reconciliation` skill; read evolution/adaptations.md first.")

    if args.fail_on_drift and split["unexplained"]:
        return CommandResult(2)
    return CommandResult(0)


def command_evolution_record(args, paths, manifest: dict) -> CommandResult:
    date_value = args.date or clock.today()
    try:
        _dt.date.fromisoformat(date_value)
    except ValueError:
        print(f"Hydra evolution record: invalid date `{date_value}`", file=sys.stderr)
        return CommandResult(1)

    entry = format_adaptation_entry(
        date_value=date_value,
        title=args.title,
        base_seed_version=args.base_seed_version or current_base_seed_version(manifest),
        paths=args.path,
        why=args.why,
        evidence=args.evidence,
        disposition=args.disposition,
    )
    errors = validate_adaptation_entries(
        parse_adaptation_ledger_text(entry), f"new adaptation record `{args.title}`"
    )
    if errors:
        print("Hydra evolution record: failed")
        for error in errors:
            print(f"- {error}")
        return CommandResult(1)

    append_adaptation_entry(paths.adaptation_ledger, entry)
    print(f"Recorded adaptation: {display_path(paths.adaptation_ledger, paths.root)}")
    return CommandResult(0)


def register(subparsers) -> None:
    """Add `diff-base` and `evolution record`."""
    diff_base = subparsers.add_parser("diff-base", help="Classify this Hydra copy against the base seed it descends from")
    diff_base.add_argument("--base", required=True, help="Path to the base repository or its .hydra-framework directory")
    diff_base.add_argument("--json", action="store_true", help="Emit machine-readable output")
    diff_base.add_argument("--fail-on-drift", action="store_true", help="Exit 2 when any unexplained difference exists")
    diff_base.set_defaults(func=_dispatch_diff_base)

    evolution = subparsers.add_parser("evolution", help="Maintain Hydra evolution records")
    evolution_sub = evolution.add_subparsers(dest="evolution_command", required=True)
    evolution_record = evolution_sub.add_parser("record", help="Append a validated adaptation-ledger entry")
    evolution_record.add_argument("--title", required=True, help="Short entry title")
    evolution_record.add_argument("--date", help="Entry date in YYYY-MM-DD; defaults to today")
    evolution_record.add_argument("--base-seed-version", help="Base seed version at time of change")
    evolution_record.add_argument(
        "--disposition",
        required=True,
        choices=sorted(ADAPTATION_DISPOSITIONS),
        help="Whether the change is repository-local or a promotion candidate",
    )
    evolution_record.add_argument("--path", action="append", required=True, help="Path touched by this adaptation")
    evolution_record.add_argument("--why", action="append", required=True, help="Evidence-backed reason")
    evolution_record.add_argument("--evidence", action="append", required=True, help="Validation or source evidence")
    evolution_record.set_defaults(func=_dispatch_evolution_record)


def _dispatch_diff_base(args, ctx) -> int:
    return command_diff_base(args, ctx.seed_paths(), ctx.resolver_paths(), ctx.manifest).exit_code


def _dispatch_evolution_record(args, ctx) -> int:
    return command_evolution_record(args, ctx.seed_paths(), ctx.manifest).exit_code
