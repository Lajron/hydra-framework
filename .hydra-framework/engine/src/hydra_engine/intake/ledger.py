"""Migration ledger status and creation."""

from __future__ import annotations

import re
from pathlib import Path

from hydra_engine.documents.tokens import display_path, write_text
from hydra_engine.intake.inventory import migration_inventory
from hydra_engine.intake.paths import IntakePaths
from hydra_engine.intake.staging import validate_migration_slug
from hydra_engine.ports import clock as clock_port

MIGRATION_LEDGER_SCHEMA = "hydra-framework.migration-ledger.v1"


def migration_workspace_matches(paths: IntakePaths, slug: str) -> list[Path]:
    root = paths.workspace_root()
    if not root.is_dir():
        return []
    pattern = re.compile(rf"\d{{4}}-\d{{2}}-\d{{2}}-{re.escape(slug)}$")
    return sorted(path for path in root.iterdir() if path.is_dir() and pattern.fullmatch(path.name))


def migration_ledger_status(paths: IntakePaths, slug: str) -> dict:
    slug = validate_migration_slug(slug)
    inventory = migration_inventory(paths, slug)
    existing = migration_workspace_matches(paths, slug)
    return {
        "schema": MIGRATION_LEDGER_SCHEMA,
        "slug": slug,
        "source_found": bool(inventory["sources"]),
        "source_path": inventory["sources"][0]["path"] if inventory["sources"] else "",
        "workspace_root": display_path(paths.workspace_root(), paths.root),
        "planned_workspace": display_path(paths.workspace_root() / f"{clock_port.today()}-{slug}", paths.root),
        "existing_workspaces": [display_path(path, paths.root) for path in existing],
        "inventory": inventory,
        "notes": [
            "ledger rows are triage scaffolding, not promotion approval",
            "creating a ledger does not move staged files or make them canonical",
        ],
    }


def markdown_cell(value: object) -> str:
    text = str(value).replace("\n", " ").replace("|", "\\|").strip()
    return text or " "


def migration_workspace_readme(slug: str, source: dict) -> str:
    classifications = ", ".join(f"{tag}: {count}" for tag, count in source["classifications"].items()) or "none"
    return "\n".join(
        [
            f"# Migration: {slug}",
            "",
            "Type: migration-workspace",
            "Status: active",
            f"Created: {clock_port.today()}",
            "Certainty: inventory-derived",
            "",
            "## Source Roots",
            "",
            "Paths in the host repository this migration is responsible for clearing.",
            "",
            (
                f"- `{source['path']}`: {source['files']} item(s), {source['bytes']} byte(s), "
                f"classifications: {classifications}"
            ),
            "",
            "## Staging Location",
            "",
            f"- Already-shared staging: `{source['path']}`",
            "- Private staging: `.hydra-framework.local/migrations/<slug>/originals/` only for private or never-tracked material",
            "- Moved on: not moved by this ledger command",
            (
                f"- Git already held this material: inventory found {source['tracked_files']} tracked file(s) "
                f"and {source['untracked_files']} untracked file(s); review before draining"
            ),
            "- Verified ignored before moving: not applicable for already-shared `.migrations/` staging",
            "",
            "## Scope",
            "",
            f"Drain staged source material under `{source['path']}` through `ledger.md`.",
            "This workspace does not promote content, merge Hydra projects, import task records, or move originals.",
            "",
            "## Definition Of Done",
            "",
            "- Source roots are empty or contain only a redirect stub.",
            "- Every `ledger.md` row has a terminal status.",
            "- Promoted meaning is under a canonical owner and validated.",
            "- Private staging is either retained deliberately or dropped deliberately, recorded here.",
            "",
            "## Related",
            "",
            "- Task record:",
            "- Triage notes:",
            "- Promotion records:",
            "- Decisions raised:",
            "",
            "## Outcome",
            "",
            "Fill in at completion: what became canonical, what was rejected, what stayed private, and where the originals ended up.",
            "",
        ]
    )


def migration_ledger_text(slug: str, source: dict) -> str:
    risk_tags = {"credential-or-private-risk", "machine-local-risk", "private-hydra-risk"}
    rows: list[list[str]] = []
    grouped_risk = 0
    grouped_risk_tags: set[str] = set()
    for finding in source["findings"]:
        tags = set(finding["classifications"])
        if tags & risk_tags:
            grouped_risk += 1
            grouped_risk_tags.update(tags & risk_tags)
            continue
        rows.append(
            [
                f"`{finding['path']}`",
                "triage",
                "TBD",
                "pending",
                ", ".join(finding["classifications"]),
            ]
        )
    if grouped_risk:
        rows.append(
            [
                f"`{source['path']}/*` ({grouped_risk} risk-classified file(s))",
                "private-review",
                "TBD",
                "pending",
                f"grouped; risk classifications: {', '.join(sorted(grouped_risk_tags))}",
            ]
        )
    row_lines = ["| Source | Verdict | Destination | Status | Notes |", "| --- | --- | --- | --- | --- |"]
    row_lines.extend("| " + " | ".join(markdown_cell(value) for value in row) + " |" for row in rows)
    if not rows:
        row_lines.append("| `none` | n/a | n/a | rejected | source inventory had no files |")
    return "\n".join(
        [
            f"# Migration Ledger: {slug}",
            "",
            "Type: migration-ledger",
            "Status: active",
            f"Created: {clock_port.today()}",
            "",
            "One row per source item. This is the only inventory; do not keep a second placement map beside it.",
            "",
            "## Status Values",
            "",
            "- `pending`: not yet triaged.",
            "- `promoted`: durable meaning is under a canonical owner and the original is drained.",
            "- `kept-private`: stays in private staging only. Nothing shareable in it.",
            "- `rejected`: no durable meaning. Recorded so nobody re-triages it.",
            "- `redirected`: original left in place as a stub pointing at the new authority.",
            "- `deferred`: real value, out of this migration's scope. Needs a follow-up owner.",
            "",
            "Terminal statuses are everything except `pending` and `deferred`. A `deferred` row must name its follow-up before the migration can close.",
            "",
            "## Ledger",
            "",
            *row_lines,
            "",
            "## Counts",
            "",
            f"- Total items: {source['files']}",
            "- Terminal: 0",
            f"- Pending: {source['files']}",
            "- Deferred: 0",
            "",
            "Update counts at each checkpoint. A migration that cannot state these numbers does not know whether it is finished.",
            "",
            "## Grouped Rows",
            "",
            "A row may cover a set when the items share one verdict and one destination.",
            "Record the count. Group rather than enumerate when the filenames are themselves sensitive.",
            "",
        ]
    )


def create_migration_ledger(paths: IntakePaths, slug: str) -> dict:
    status = migration_ledger_status(paths, slug)
    if not status["source_found"]:
        raise ValueError(f"no staged source found at .migrations/{slug}")
    if status["existing_workspaces"]:
        raise FileExistsError(
            f"migration ledger already exists for `{slug}`: {', '.join(status['existing_workspaces'])}"
        )
    workspace = paths.workspace_root() / f"{clock_port.today()}-{slug}"
    if workspace.exists():
        raise FileExistsError(f"migration workspace already exists: {display_path(workspace, paths.root)}")
    source = status["inventory"]["sources"][0]
    write_text(workspace / "README.md", migration_workspace_readme(slug, source))
    write_text(workspace / "ledger.md", migration_ledger_text(slug, source))
    status["created_workspace"] = display_path(workspace, paths.root)
    status["existing_workspaces"] = [display_path(workspace, paths.root)]
    return status
