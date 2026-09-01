"""Telemetry command family."""

from __future__ import annotations

import json
import sys
import uuid
from pathlib import Path

from hydra_engine.commands import CommandResult
from hydra_engine.documents.tokens import display_path
from hydra_engine.identity.slugs import slugify
from hydra_engine.ports import clock
from hydra_engine.telemetry import evidence_mint, gate, reporting
from hydra_engine.work.owners import HydraOwnerError, resolve_owner


def command_gate(args, ctx) -> CommandResult:
    attestation = gate.run_gate(
        local=ctx.local,
        hydra=ctx.hydra,
        max_spillover_per_1000=args.max_spillover_per_1000,
        min_event_count=args.min_event_count,
        min_event_kinds=args.min_event_kinds,
    )
    content = json.dumps(attestation.as_dict(), indent=2, sort_keys=True) + "\n"
    if args.output:
        output = Path(args.output)
        if not output.is_absolute():
            output = ctx.root / output
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(content, encoding="utf-8")
    print(content, end="")
    return CommandResult(0 if attestation.verdict == "pass" else 1)


def command_report(args, ctx) -> CommandResult:
    report = reporting.build_report(ctx.local)
    if args.json:
        print(json.dumps(report, indent=2, sort_keys=True))
        return CommandResult(0)
    print(f"events: {report['event_count']} across {report['distinct_event_kinds']} kind(s), {report['distinct_field_names']} field(s)")
    for kind in sorted(report["counts_by_kind"]):
        print(f"  {kind}: {report['counts_by_kind'][kind]}")
    if "reducer_coverage" in report:
        coverage = report["reducer_coverage"]
        print(f"reducer coverage: {coverage['had_reducer']}/{coverage['total']} had a reducer")
    return CommandResult(0)


def command_evidence_create(args, ctx) -> CommandResult:
    try:
        owner = resolve_owner(args.owner, ctx.env_owner(), ctx.git_email())
    except HydraOwnerError as error:
        print(str(error), file=sys.stderr)
        return CommandResult(1)

    attestation = gate.run_gate(local=ctx.local, hydra=ctx.hydra)
    if attestation.verdict != "pass":
        print(f"telemetry gate verdict is `{attestation.verdict}`; a failing attestation is not evidence", file=sys.stderr)
        return CommandResult(1)

    today = clock.today()
    slug = slugify(args.slug)
    dir_name = evidence_mint.package_dir_name(today, owner, slug)
    package_dir = ctx.hydra / "repo" / "telemetry" / "packages" / dir_name
    if package_dir.exists():
        print(f"{display_path(package_dir, ctx.root)} already exists", file=sys.stderr)
        return CommandResult(1)

    package_dir.mkdir(parents=True)
    report = reporting.build_report(ctx.local)
    (package_dir / "metrics.json").write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    (package_dir / "gate-attestation.json").write_text(json.dumps(attestation.as_dict(), indent=2, sort_keys=True) + "\n", encoding="utf-8")
    overview = evidence_mint.render_overview(dir_name=dir_name, uid=str(uuid.uuid4()), owner=owner, today=today, title=args.question)
    (package_dir / "overview.md").write_text(overview, encoding="utf-8")

    print(f"Created {display_path(package_dir, ctx.root)}")
    print("Fill in `## Question` (already seeded), `## Findings`, and `## Method` before absorption.")
    return CommandResult(0)


def register(subparsers) -> None:
    telemetry = subparsers.add_parser("telemetry", help="Inspect, report on, and gate local telemetry capture")
    telemetry_sub = telemetry.add_subparsers(dest="telemetry_command", required=True)
    gate_cmd = telemetry_sub.add_parser("gate", help="Run the telemetry redaction gate")
    gate_cmd.add_argument("--output", help="Write the committable attestation JSON to a file")
    gate_cmd.add_argument("--max-spillover-per-1000", type=int, help="Maximum unpoisoned spillover fields per 1000")
    gate_cmd.add_argument("--min-event-count", type=int, help="Minimum synthetic plus local event rows")
    gate_cmd.add_argument("--min-event-kinds", type=int, help="Minimum distinct event kinds")
    gate_cmd.set_defaults(func=_dispatch_gate)

    report_cmd = telemetry_sub.add_parser("report", help="Derived aggregates over the private telemetry corpus")
    report_cmd.add_argument("--json", action="store_true", help="Emit the bounded aggregate JSON a telemetry evidence package's metrics.json accepts")
    report_cmd.set_defaults(func=_dispatch_report)

    evidence_parser = telemetry_sub.add_parser("evidence", help="Telemetry evidence package operations")
    evidence_sub = evidence_parser.add_subparsers(dest="telemetry_evidence_command", required=True)
    create_cmd = evidence_sub.add_parser("create", help="Mint a telemetry evidence package from a real gate run")
    create_cmd.add_argument("--slug", required=True, help="Short slug naming the question")
    create_cmd.add_argument("--question", required=True, help="The question this package answers")
    create_cmd.add_argument("--owner", default="", help="Owner slug override (default: HYDRA_OWNER or git config user.email)")
    create_cmd.set_defaults(func=_dispatch_evidence_create)


def _dispatch_gate(args, ctx) -> int:
    if args.max_spillover_per_1000 is None:
        args.max_spillover_per_1000 = ctx.threshold_value("hydra_engine.telemetry.gate.GATE_MAX_SPILLOVER_PER_1000")
    if args.min_event_count is None:
        args.min_event_count = ctx.threshold_value("hydra_engine.telemetry.gate.GATE_MIN_EVENT_COUNT")
    if args.min_event_kinds is None:
        args.min_event_kinds = ctx.threshold_value("hydra_engine.telemetry.gate.GATE_MIN_EVENT_KINDS")
    return command_gate(args, ctx).exit_code


def _dispatch_report(args, ctx) -> int:
    return command_report(args, ctx).exit_code


def _dispatch_evidence_create(args, ctx) -> int:
    return command_evidence_create(args, ctx).exit_code
