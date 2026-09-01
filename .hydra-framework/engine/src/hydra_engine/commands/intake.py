"""intake command decisions."""

from __future__ import annotations

import json
import sys
from pathlib import Path

from hydra_engine.commands import CommandResult
from hydra_engine.intake import approval
from hydra_engine.intake.inventory import migration_inventory
from hydra_engine.intake.ledger import create_migration_ledger, migration_ledger_status
from hydra_engine.intake.paths import IntakePaths

MIGRATION_INVENTORY_FINDING_REPORT_LIMIT = 20


def _read_json_object(root: Path, raw_path: str, label: str) -> dict:
    path = Path(raw_path)
    path = path if path.is_absolute() else root / path
    resolved = path.resolve()
    if not resolved.is_relative_to(root.resolve()):
        raise ValueError(f"{label} must be inside the repository root: {raw_path}")
    data = json.loads(resolved.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"{label} must contain one JSON object: {raw_path}")
    return data


def _render_batch_state(state: dict, as_json: bool) -> None:
    if as_json:
        print(json.dumps(state, indent=2))
        return
    print("Hydra migration batch")
    for key, label in (("slug", "Slug"), ("batch", "Batch"), ("phase", "Phase"), ("revision", "Revision")):
        if key in state:
            print(f"{label}: {state[key]}")
    gate = state.get("current_approval")
    if isinstance(gate, dict):
        print(f"Approval: {gate.get('kind') or gate.get('gate') or gate.get('type') or 'pending'}")
        reasons = gate.get("reasons", [])
        if isinstance(reasons, list) and reasons:
            print("Reasons:")
            for reason in reasons:
                print(f"- {reason}")
        action = gate.get("action")
        if action:
            print("Action:")
            print(json.dumps(action, indent=2))


def _run_batch_action(args, paths: IntakePaths, action) -> CommandResult:
    try:
        state = action()
    except (OSError, UnicodeError, ValueError, json.JSONDecodeError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return CommandResult(1)
    _render_batch_state(state, args.json)
    return CommandResult(0)


def command_migration_request_stage(args, paths: IntakePaths) -> CommandResult:
    sources = [{"path": source, "route": args.route} for source in args.source]
    return _run_batch_action(
        args,
        paths,
        lambda: approval.request_staging(
            paths,
            args.slug,
            args.batch,
            sources,
            drafting_chain=args.worker_instance,
            capability_class=args.capability_class,
        ),
    )


def command_migration_propose(args, paths: IntakePaths) -> CommandResult:
    return _run_batch_action(
        args,
        paths,
        lambda: approval.submit_proposal(
            paths, args.slug, args.batch, _read_json_object(paths.root, args.manifest, "proposal manifest")
        ),
    )


def command_migration_validate_batch(args, paths: IntakePaths) -> CommandResult:
    return _run_batch_action(
        args,
        paths,
        lambda: approval.record_validation(
            paths, args.slug, args.batch, _read_json_object(paths.root, args.evidence, "validation evidence")
        ),
    )


def command_migration_request_close(args, paths: IntakePaths) -> CommandResult:
    return _run_batch_action(
        args,
        paths,
        lambda: approval.request_closure(
            paths,
            args.slug,
            args.batch,
            _read_json_object(paths.root, args.reconciliation, "reconciliation manifest"),
        ),
    )


def command_migration_decide(args, paths: IntakePaths) -> CommandResult:
    return _run_batch_action(
        args,
        paths,
        lambda: approval.decide(
            paths,
            args.slug,
            args.batch,
            args.outcome,
            rationale=args.rationale,
            guidance=args.guidance,
            actor=args.actor,
        ),
    )


def command_migration_status(args, paths: IntakePaths) -> CommandResult:
    return _run_batch_action(args, paths, lambda: approval.batch_status(paths, args.slug, args.batch))


def command_migration_inventory(args, paths: IntakePaths) -> CommandResult:
    try:
        inventory = migration_inventory(paths, args.slug or "")
    except ValueError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return CommandResult(1)
    if args.json:
        print(json.dumps(inventory, indent=2))
        return CommandResult(0)

    print("Hydra migration inventory")
    print(f"Staging root: {inventory['staging_root']}")
    if not inventory["exists"]:
        print("Status: missing")
    print(
        f"Totals: {inventory['totals']['sources']} source(s), "
        f"{inventory['totals']['files']} file(s), "
        f"{inventory['totals']['directories']} dir(s), "
        f"{inventory['totals']['bytes']} byte(s)"
    )
    for note in inventory["notes"]:
        print(f"Note: {note}")
    for source in inventory["sources"]:
        print("")
        print(f"- {source['slug']}: {source['path']}")
        print(
            f"  files: {source['files']}, directories: {source['directories']}, "
            f"bytes: {source['bytes']}, tracked: {source['tracked_files']}, "
            f"untracked: {source['untracked_files']}"
        )
        if source["classifications"]:
            print("  classifications:")
            for tag, count in source["classifications"].items():
                print(f"    - {tag}: {count}")
        for finding in source["findings"][:MIGRATION_INVENTORY_FINDING_REPORT_LIMIT]:
            print(f"  - {finding['path']}: {', '.join(finding['classifications'])}")
        if len(source["findings"]) > MIGRATION_INVENTORY_FINDING_REPORT_LIMIT:
            print(f"  - ... {len(source['findings']) - MIGRATION_INVENTORY_FINDING_REPORT_LIMIT} more file(s)")
    return CommandResult(0)


def command_migration_ledger(args, paths: IntakePaths) -> CommandResult:
    try:
        status = create_migration_ledger(paths, args.slug) if args.create else migration_ledger_status(paths, args.slug)
    except (FileExistsError, ValueError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return CommandResult(1)
    if args.json:
        print(json.dumps(status, indent=2))
        return CommandResult(0)

    print("Hydra migration ledger")
    print(f"Slug: {status['slug']}")
    print(f"Source: {status['source_path'] or 'not found'}")
    print(f"Workspace root: {status['workspace_root']}")
    if status.get("created_workspace"):
        print(f"Created workspace: {status['created_workspace']}")
    elif status["existing_workspaces"]:
        print("Existing workspace(s):")
        for workspace in status["existing_workspaces"]:
            print(f"- {workspace}")
    else:
        print(f"Planned workspace: {status['planned_workspace']}")
    for note in status["notes"]:
        print(f"Note: {note}")
    return CommandResult(0)


def register(subparsers) -> None:
    """Add the migration inventory, ledger, and approval-gated batch flow."""
    migration = subparsers.add_parser("migration", help="Inspect staged migration source material")
    migration_sub = migration.add_subparsers(dest="migration_command", required=True)

    inventory = migration_sub.add_parser("inventory", help="Classify already-shared material staged under .migrations/")
    inventory.add_argument("slug", nargs="?", help="Optional .migrations/<slug> source root to inventory")
    inventory.add_argument("--json", action="store_true", help="Emit machine-readable inventory")
    inventory.set_defaults(func=_dispatch_migration_inventory)

    ledger = migration_sub.add_parser("ledger", help="Report or create a migration ledger for one staged source")
    ledger.add_argument("slug", help="Simple .migrations/<slug> source root")
    ledger.add_argument("--create", action="store_true", help="Create the shared intake migration workspace")
    ledger.add_argument("--json", action="store_true", help="Emit machine-readable ledger status")
    ledger.set_defaults(func=_dispatch_migration_ledger)

    request_stage = migration_sub.add_parser(
        "request-stage", help="Inventory source roots and request approval for an exact staging move"
    )
    request_stage.add_argument("slug", help="Simple migration source slug")
    request_stage.add_argument("batch", help="Simple bounded batch slug")
    request_stage.add_argument("--source", action="append", required=True, help="Repository-relative source root; repeat for a bounded set")
    request_stage.add_argument("--route", choices=("shared", "private"), required=True, help="Approved staging tier")
    request_stage.add_argument("--worker-instance", action="append", required=True, help="Provider-neutral drafting-chain instance id; repeat as needed")
    request_stage.add_argument("--capability-class", required=True, help="Provider-neutral worker capability class")
    request_stage.add_argument("--json", action="store_true", help="Emit machine-readable batch state")
    request_stage.set_defaults(func=_dispatch_migration_request_stage)

    propose = migration_sub.add_parser("propose", help="Submit a bounded package/unit proposal for validation")
    propose.add_argument("slug")
    propose.add_argument("batch")
    propose.add_argument("--manifest", required=True, help="JSON proposal manifest")
    propose.add_argument("--json", action="store_true", help="Emit machine-readable batch state")
    propose.set_defaults(func=_dispatch_migration_propose)

    validate_batch = migration_sub.add_parser(
        "validate-batch", help="Record fresh independent validator evidence and request publication approval"
    )
    validate_batch.add_argument("slug")
    validate_batch.add_argument("batch")
    validate_batch.add_argument("--evidence", required=True, help="JSON independent-validation evidence")
    validate_batch.add_argument("--json", action="store_true", help="Emit machine-readable batch state")
    validate_batch.set_defaults(func=_dispatch_migration_validate_batch)

    request_close = migration_sub.add_parser(
        "request-close", help="Reconcile every item and request approval for exact staged-original removal"
    )
    request_close.add_argument("slug")
    request_close.add_argument("batch")
    request_close.add_argument("--reconciliation", required=True, help="JSON reconciliation and exact removal manifest")
    request_close.add_argument("--json", action="store_true", help="Emit machine-readable batch state")
    request_close.set_defaults(func=_dispatch_migration_request_close)

    decide = migration_sub.add_parser("decide", help="Approve, reject, or revise the batch's current human gate")
    decide.add_argument("slug")
    decide.add_argument("batch")
    decide.add_argument("outcome", choices=("approve", "reject", "revise"))
    decide.add_argument("--actor", default="", help="Human or review authority recording the outcome")
    decide.add_argument("--rationale", default="", help="Required terminal rationale for rejection")
    decide.add_argument("--guidance", default="", help="Required guidance for revision")
    decide.add_argument("--json", action="store_true", help="Emit machine-readable batch state")
    decide.set_defaults(func=_dispatch_migration_decide)

    status = migration_sub.add_parser("status", help="Report one approval-gated migration batch")
    status.add_argument("slug")
    status.add_argument("batch")
    status.add_argument("--json", action="store_true", help="Emit machine-readable batch state")
    status.set_defaults(func=_dispatch_migration_status)


def _dispatch_migration_inventory(args, ctx) -> int:
    return command_migration_inventory(args, ctx.intake_paths()).exit_code


def _dispatch_migration_ledger(args, ctx) -> int:
    return command_migration_ledger(args, ctx.intake_paths()).exit_code


def _dispatch_migration_request_stage(args, ctx) -> int:
    return command_migration_request_stage(args, ctx.intake_paths()).exit_code


def _dispatch_migration_propose(args, ctx) -> int:
    return command_migration_propose(args, ctx.intake_paths()).exit_code


def _dispatch_migration_validate_batch(args, ctx) -> int:
    return command_migration_validate_batch(args, ctx.intake_paths()).exit_code


def _dispatch_migration_request_close(args, ctx) -> int:
    return command_migration_request_close(args, ctx.intake_paths()).exit_code


def _dispatch_migration_decide(args, ctx) -> int:
    return command_migration_decide(args, ctx.intake_paths()).exit_code


def _dispatch_migration_status(args, ctx) -> int:
    return command_migration_status(args, ctx.intake_paths()).exit_code
