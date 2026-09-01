"""providers command decisions."""

from __future__ import annotations

import json
import sys

from hydra_engine.commands import CommandResult
from hydra_engine.config import ConfigError
from hydra_engine.documents.tokens import HydraYamlError, display_path, read_text, write_text
from hydra_engine.providers.adapter_plan import planned_adapter_files
from hydra_engine.providers.paths import ProvidersPaths
from hydra_engine.providers.reclaim import classify_surfaces, promote_surface


def command_export_adapters(args, paths: ProvidersPaths) -> CommandResult:
    try:
        plan = planned_adapter_files(paths)
    except (HydraYamlError, ConfigError) as error:
        print(f"Hydra export failed: {error}", file=sys.stderr)
        return CommandResult(1)
    if not plan:
        print("No Hydra skills or agents found to export.")
        return CommandResult(0)

    created = [path for path in sorted(plan) if not path.exists()]
    changed = [
        path for path in sorted(plan) if path.exists() and read_text(path) != plan[path]
    ]

    if args.check:
        if not created and not changed:
            print(f"Hydra adapters: up to date ({len(plan)} generated files)")
            return CommandResult(0)
        print("Hydra adapters: drift detected")
        for path in created:
            print(f"- missing: {display_path(path, paths.root)}")
        for path in changed:
            print(f"- stale: {display_path(path, paths.root)}")
        print("Run `hydra.py export-adapters` to regenerate.")
        return CommandResult(1)

    if args.dry_run:
        if not created and not changed:
            print(f"Hydra adapters: no changes ({len(plan)} generated files)")
            return CommandResult(0)
        print("Hydra adapters: would write")
        for path in created:
            print(f"- create: {display_path(path, paths.root)}")
        for path in changed:
            print(f"- update: {display_path(path, paths.root)}")
        return CommandResult(0)

    for path in created + changed:
        write_text(path, plan[path])

    if not created and not changed:
        print(f"Hydra adapters: already current ({len(plan)} generated files)")
        return CommandResult(0)
    print(f"Hydra adapters: wrote {len(created) + len(changed)} of {len(plan)} generated files")
    for path in created:
        print(f"- create: {display_path(path, paths.root)}")
    for path in changed:
        print(f"- update: {display_path(path, paths.root)}")
    return CommandResult(0)


def command_reclaim(args, paths: ProvidersPaths) -> CommandResult:
    """Report, and optionally promote, provider files Hydra does not own."""
    items = classify_surfaces(paths)
    if args.json:
        print(json.dumps(items, indent=2))
        return CommandResult(0)

    buckets: dict[str, list[dict[str, str]]] = {}
    for item in items:
        buckets.setdefault(item["status"], []).append(item)

    generated = len(buckets.get("generated", []))
    orphaned = buckets.get("orphaned", [])
    drifted = buckets.get("drifted", [])
    stale = buckets.get("stale", [])

    print(f"Hydra provider surfaces: {len(items)} file(s)")
    print(f"- generated and current: {generated}")
    for label, group in [("orphaned", orphaned), ("drifted", drifted), ("stale", stale)]:
        print(f"- {label}: {len(group)}")
        for item in group:
            print(f"  {item['path']}: {item['detail']}")

    if not orphaned and not drifted and not stale:
        print("\nAll provider files are generated from canonical Hydra sources.")
        return CommandResult(0)

    if args.promote and orphaned:
        promoted: list = []
        skipped: list[str] = []
        for item in orphaned:
            target = promote_surface(paths, item)
            if target is None:
                skipped.append(item["path"])
            else:
                promoted.append(target)
        print("")
        for target in promoted:
            print(f"promoted: {display_path(target, paths.root)}")
        for path in skipped:
            print(f"skipped (canonical target already exists): {path}")
        if promoted:
            print("\nReview each promoted file, then run `hydra.py export-adapters`.")
            print("Promoted metadata is marked `certainty: inferred` and `scope: repo-local`.")
        return CommandResult(0)

    print("\nWhat to do:")
    if orphaned:
        print("- orphaned: someone authored these directly in a provider directory.")
        print("  Promote with `hydra.py reclaim --promote`, then review and re-export.")
    if drifted:
        print("- drifted: the generated wrapper was edited instead of its canonical source.")
        print("  Move the edit into the canonical file, then run `hydra.py export-adapters`.")
    if stale:
        print("- stale: canonical source is gone or no longer exported. Delete the wrapper.")
    return CommandResult(1 if args.fail_on_findings else 0)


def register(subparsers) -> None:
    """Add `export-adapters` and `reclaim`."""
    export = subparsers.add_parser(
        "export-adapters",
        help="Generate provider skill and subagent wrappers from canonical Hydra capabilities",
    )
    export.add_argument("--check", action="store_true", help="Exit non-zero if any generated surface is missing or stale")
    export.add_argument("--dry-run", action="store_true", help="Report what would be written without writing")
    export.set_defaults(func=_dispatch_export_adapters)

    reclaim = subparsers.add_parser(
        "reclaim",
        help="Find provider files Hydra does not own and plan their promotion into canonical Hydra",
    )
    reclaim.add_argument("--promote", action="store_true", help="Move hand-authored provider files into canonical Hydra")
    reclaim.add_argument("--json", action="store_true", help="Emit machine-readable output")
    reclaim.add_argument("--fail-on-findings", action="store_true", help="Exit non-zero when unmanaged files exist")
    reclaim.set_defaults(func=_dispatch_reclaim)


def _dispatch_export_adapters(args, ctx) -> int:
    return command_export_adapters(args, ctx.providers_paths()).exit_code


def _dispatch_reclaim(args, ctx) -> int:
    return command_reclaim(args, ctx.providers_paths()).exit_code
