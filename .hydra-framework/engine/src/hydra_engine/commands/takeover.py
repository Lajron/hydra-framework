"""takeover command implementation."""

from __future__ import annotations

import json
import sys
from pathlib import Path

from hydra_engine.commands import CommandResult
from hydra_engine.intake.takeover_scan import takeover_scan

TAKEOVER_FINDING_REPORT_LIMIT = 10


def command_takeover_scan(args, ctx) -> CommandResult:
    raw_root = Path(args.root) if args.root else ctx.root
    root = raw_root if raw_root.is_absolute() else ctx.root / raw_root
    report = takeover_scan(root)
    if not report["exists"]:
        print(f"error: root is not a directory: {root}", file=sys.stderr)
        if args.json:
            print(json.dumps(report, indent=2))
        return CommandResult(1)
    if args.json:
        print(json.dumps(report, indent=2))
        return CommandResult(0)

    print("Hydra takeover scan")
    print(f"Root: {report['root']}")
    print(f"Totals: {report['totals']['candidates']} candidate root(s), {report['totals']['files']} file(s)")
    for note in report["notes"]:
        print(f"Note: {note}")
    for candidate in report["candidates"]:
        print("")
        print(f"- {candidate['path']} ({candidate['source']}): {candidate['classification']}")
        print(
            f"  files: {candidate['files']}, tracked: {candidate['git']['tracked_files']}, "
            f"untracked: {candidate['git']['untracked_files']}, ignored: {candidate['git']['ignored_files']}"
        )
        if candidate["provider_surface_counts"]:
            summary = ", ".join(f"{status}: {count}" for status, count in candidate["provider_surface_counts"].items())
            print(f"  provider surfaces: {summary}")
        if candidate["classifications"]:
            summary = ", ".join(f"{tag}: {count}" for tag, count in candidate["classifications"].items())
            print(f"  intake tags: {summary}")
        print(f"  staging: {candidate['staging']['route']}")
        if candidate["staging"]["path"]:
            print(f"  staging path: {candidate['staging']['path']}")
        for reason in candidate["reasons"]:
            print(f"  reason: {reason}")
        for finding in candidate["findings"][:TAKEOVER_FINDING_REPORT_LIMIT]:
            print(f"  - {finding['path']}: {', '.join(finding['classifications'])}")
        extra = len(candidate["findings"]) - TAKEOVER_FINDING_REPORT_LIMIT
        if extra > 0:
            print(f"  - ... {extra} more file(s)")
    return CommandResult(0)


def register(subparsers) -> None:
    takeover = subparsers.add_parser("takeover", help="Inspect existing AI architecture before migration staging")
    takeover_sub = takeover.add_subparsers(dest="takeover_command", required=True)

    scan = takeover_sub.add_parser("scan", help="Read-only scan for takeover candidate roots")
    scan.add_argument("--root", help="Repository root to scan; defaults to the current Hydra repository")
    scan.add_argument("--json", action="store_true", help="Emit machine-readable scan output")
    scan.set_defaults(func=_dispatch_takeover_scan)


def _dispatch_takeover_scan(args, ctx) -> int:
    return command_takeover_scan(args, ctx).exit_code
