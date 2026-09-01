"""integrate command implementation."""

from __future__ import annotations

import json
import sys

from hydra_engine.commands import CommandResult
from hydra_engine.intake.integration import (
    create_integration_workspace,
    integration_object_map,
    integration_scan,
    integration_status,
    write_integration_object_map,
)


def _print_scan(report: dict) -> None:
    print("Hydra source integration scan")
    print(f"Slug: {report['slug']}")
    print(f"Source: {report['source_path'] or 'not found'}")
    print(f"Hydra source: {'found' if report['hydra_found'] else 'missing'}")
    print(f"Project: {report['project_name']}")
    print(f"Seed version: {report['seed_version']}")
    print(
        f"Objects: {report['objects']['total']} total, "
        f"{report['capabilities']} capability object(s), "
        f"{report['knowledge_packages']} knowledge package(s)"
    )
    print(
        f"Collisions: {len(report['id_collisions'])} id, "
        f"{len(report['path_collisions'])} path"
    )
    print(f"Planned workspace: {report['planned_workspace']}")
    if report["existing_workspaces"]:
        print("Existing workspace(s):")
        for workspace in report["existing_workspaces"]:
            print(f"- {workspace}")
    for note in report["notes"]:
        print(f"Note: {note}")


def command_integrate_scan(args, ctx) -> CommandResult:
    try:
        report = integration_scan(ctx.intake_paths(), args.slug, ctx.resolver_paths())
    except ValueError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return CommandResult(1)
    if args.json:
        print(json.dumps(report, indent=2))
        return CommandResult(0)
    _print_scan(report)
    return CommandResult(0)


def command_integrate_identify(args, ctx) -> CommandResult:
    try:
        result = write_integration_object_map(ctx.intake_paths(), args.slug, ctx.resolver_paths())
    except (FileExistsError, ValueError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return CommandResult(1)
    print("Hydra source integration identify")
    print(f"Slug: {result['slug']}")
    print(f"Workspace: {result['workspace']}")
    print(f"Object map: {result['object_map']}")
    print(f"Objects: {result['objects']}")
    return CommandResult(0)


def command_integrate_map(args, ctx) -> CommandResult:
    try:
        report = (
            create_integration_workspace(ctx.intake_paths(), args.slug, ctx.resolver_paths())
            if args.create else
            integration_scan(ctx.intake_paths(), args.slug, ctx.resolver_paths())
        )
        mapping = integration_object_map(ctx.intake_paths(), args.slug, ctx.resolver_paths())
    except (FileExistsError, ValueError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return CommandResult(1)
    print("Hydra source integration map")
    print(f"Slug: {report['slug']}")
    print(f"Source: {report['source_path'] or 'not found'}")
    if report.get("created_workspace"):
        print(f"Created workspace: {report['created_workspace']}")
    elif report["existing_workspaces"]:
        print("Existing workspace(s):")
        for workspace in report["existing_workspaces"]:
            print(f"- {workspace}")
    else:
        print(f"Planned workspace: {report['planned_workspace']}")
    print(f"Rows: {len(mapping['objects'])}")
    print(f"Links: {len([row for row in mapping['objects'] if row['local_id']])}")
    print(f"Imports: {len([row for row in mapping['objects'] if not row['local_id']])}")
    return CommandResult(0)


def command_integrate_status(args, ctx) -> CommandResult:
    try:
        status = integration_status(ctx.intake_paths(), args.slug)
    except ValueError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return CommandResult(1)
    if args.json:
        print(json.dumps(status, indent=2))
        return CommandResult(0)
    print("Hydra source integration status")
    print(f"Slug: {status['slug']}")
    print(f"Workspace: {status['workspace'] or 'not found'}")
    print(
        f"Progress: {status['progress']['terminal']} terminal, "
        f"{status['progress']['open']} open, {status['progress']['total']} total"
    )
    print(
        f"Collisions: {status['collisions']['id']} id, "
        f"{status['collisions']['path']} path, {status['collisions']['ambiguous']} ambiguous"
    )
    if status["missing_files"]:
        print("Missing file(s):")
        for path in status["missing_files"]:
            print(f"- {path}")
    for note in status["notes"]:
        print(f"Note: {note}")
    return CommandResult(0)


def register(subparsers) -> None:
    integrate = subparsers.add_parser("integrate", help="Inspect and map staged Hydra source projects")
    integrate_sub = integrate.add_subparsers(dest="integrate_command", required=True)

    scan = integrate_sub.add_parser("scan", help="Read-only scan of a staged Hydra source")
    scan.add_argument("slug", help="Simple .migrations/<slug> source root")
    scan.add_argument("--json", action="store_true", help="Emit machine-readable scan output")
    scan.set_defaults(func=_dispatch_integrate_scan)

    identify = integrate_sub.add_parser("identify", help="Write source-scoped object identities into object-map.yaml")
    identify.add_argument("slug", help="Simple .migrations/<slug> source root")
    identify.set_defaults(func=_dispatch_integrate_identify)

    map_command = integrate_sub.add_parser("map", help="Report or create a source integration workspace")
    map_command.add_argument("slug", help="Simple .migrations/<slug> source root")
    map_command.add_argument("--create", action="store_true", help="Create the source integration workspace")
    map_command.set_defaults(func=_dispatch_integrate_map)

    status = integrate_sub.add_parser("status", help="Summarize source integration workspace progress")
    status.add_argument("slug", help="Simple .migrations/<slug> source root")
    status.add_argument("--json", action="store_true", help="Emit machine-readable status output")
    status.set_defaults(func=_dispatch_integrate_status)


def _dispatch_integrate_scan(args, ctx) -> int:
    return command_integrate_scan(args, ctx).exit_code


def _dispatch_integrate_identify(args, ctx) -> int:
    return command_integrate_identify(args, ctx).exit_code


def _dispatch_integrate_map(args, ctx) -> int:
    return command_integrate_map(args, ctx).exit_code


def _dispatch_integrate_status(args, ctx) -> int:
    return command_integrate_status(args, ctx).exit_code
