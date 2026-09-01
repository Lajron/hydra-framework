"""Source integration workspace file rendering and status helpers."""

import json
import re
from pathlib import Path

from hydra_engine.documents.tokens import display_path, read_text, write_text
from hydra_engine.intake.ledger import markdown_cell
from hydra_engine.ports import clock as clock_port

SOURCE_OBJECT_MAP_SCHEMA = "hydra-framework.source-object-map.v1"
SOURCE_COLLISIONS_SCHEMA = "hydra-framework.source-collisions.v1"
SOURCE_INTEGRATION_STATUS_SCHEMA = "hydra-framework.source-integration-status.v1"

EXPECTED_FILES = ["README.md", "ledger.md", "object-map.yaml", "collisions.yaml"]
TERMINAL_STATUSES = {"promoted", "kept-private", "rejected", "redirected"}
OPEN_STATUSES = {"pending", "deferred"}


def matches(paths, slug: str) -> list[Path]:
    root = paths.integration_workspace_root()
    if not root.is_dir():
        return []
    pattern = re.compile(rf"\d{{4}}-\d{{2}}-\d{{2}}-{re.escape(slug)}$")
    return sorted(path for path in root.iterdir() if path.is_dir() and pattern.fullmatch(path.name))


def planned_display_path(paths, slug: str) -> str:
    return display_path(paths.integration_workspace_root() / f"{clock_port.today()}-{slug}", paths.root)


def created_date() -> str:
    return clock_port.today()


def _quote(value: str) -> str:
    return json.dumps(value)


def object_map_text(mapping: dict) -> str:
    lines = [
        f"schema: {SOURCE_OBJECT_MAP_SCHEMA}",
        f"slug: {mapping['slug']}",
        f"source_path: {mapping['source_path']}",
        f"created: {mapping['created']}",
        "objects:",
    ]
    for row in mapping["objects"]:
        lines.extend([
            f"  - source_id: {row['source_id']}",
            f"    original_id: {row['original_id']}",
            f"    uid: {_quote(row['uid'])}",
            f"    kind: {row['kind']}",
            f"    family: {_quote(row['family'])}",
            f"    title: {_quote(row['title'])}",
            f"    source_path: {row['source_path']}",
            f"    source_envelope_path: {row['source_envelope_path']}",
            f"    digest: {row['digest']}",
            f"    match_method: {row['match_method']}",
            f"    match_count: {row['match_count']}",
            f"    local_id: {_quote(row['local_id'])}",
            f"    local_path: {_quote(row['local_path'])}",
            f"    verdict: {row['verdict']}",
            f"    status: {row['status']}",
        ])
    return "\n".join(lines) + "\n"


def collisions(scan: dict, mapping: dict) -> dict:
    ambiguous = [
        {
            "source_id": row["source_id"],
            "original_id": row["original_id"],
            "match_method": row["match_method"],
            "match_count": row["match_count"],
        }
        for row in mapping["objects"]
        if str(row["match_method"]).startswith("ambiguous-")
    ]
    return {
        "schema": SOURCE_COLLISIONS_SCHEMA,
        "slug": scan["slug"],
        "id_collisions": scan["id_collisions"],
        "path_collisions": scan["path_collisions"],
        "ambiguous_matches": ambiguous,
    }


def collisions_text(value: dict) -> str:
    lines = [f"schema: {SOURCE_COLLISIONS_SCHEMA}", f"slug: {value['slug']}"]
    for key in ("id_collisions", "path_collisions", "ambiguous_matches"):
        lines.append(f"{key}:")
        if value[key]:
            for row in value[key]:
                lines.append("  - type: collision")
                for name, item in row.items():
                    lines.append(f"    {name}: {_quote(str(item))}")
        else:
            lines.append("  - none")
    return "\n".join(lines) + "\n"


def readme_text(scan: dict) -> str:
    risk = ", ".join(f"{key}: {value}" for key, value in scan["private_material_risk"].items()) or "none"
    surfaces = ", ".join(f"{key}: {value}" for key, value in scan["generated_surfaces"].items()) or "none"
    return "\n".join([
        f"# Source Integration: {scan['slug']}",
        "",
        "Type: source-integration",
        "Status: active",
        f"Created: {clock_port.today()}",
        "Certainty: scan-derived",
        "",
        "## Source Manifest",
        "",
        f"- Source project: {scan['project_name']}",
        f"- Source root: `{scan['source_path']}`",
        f"- Seed version: {scan['seed_version']}",
        f"- Lineage: {scan['lineage'] or {}}",
        "",
        "## Source Summary",
        "",
        f"- Objects: {scan['objects']['total']}",
        f"- Capabilities: {scan['capabilities']}",
        f"- Knowledge packages: {scan['knowledge_packages']}",
        f"- Migration workspaces: {scan['migrations']['workspaces']}",
        f"- Generated surfaces: {surfaces}",
        f"- Private-material risk: {risk}",
        "",
        "## Workspace Files",
        "",
        "- `ledger.md`: object/capability triage rows.",
        "- `object-map.yaml`: source-scoped ids and proposed local links.",
        "- `collisions.yaml`: id, path, and ambiguous-match collisions.",
        "",
    ])


def ledger_text(scan: dict, mapping: dict) -> str:
    rows = ["| Source Object | Source ID | Verdict | Destination | Status | Notes |", "| --- | --- | --- | --- | --- | --- |"]
    for row in mapping["objects"]:
        destination = row["local_path"] if row["local_path"] else "TBD"
        notes = f"{row['family']} / {row['kind']}; match: {row['match_method']}"
        rows.append("| " + " | ".join(markdown_cell(value) for value in [
            f"`{row['original_id']}`",
            f"`{row['source_id']}`",
            row["verdict"],
            destination,
            row["status"],
            notes,
        ]) + " |")
    if not mapping["objects"]:
        rows.append("| `none` | `none` | reject | rejected | rejected | source scan found no Hydra objects |")
    return "\n".join([
        f"# Source Integration Ledger: {scan['slug']}",
        "",
        "Type: source-integration-ledger",
        "Status: active",
        f"Created: {clock_port.today()}",
        "",
        "Rows track source object decisions. The staged source tree is not modified by this workspace.",
        "",
        "## Ledger",
        "",
        *rows,
        "",
        "## Counts",
        "",
        f"- Total rows: {len(mapping['objects'])}",
        "- Terminal: 0",
        f"- Open: {len(mapping['objects'])}",
        "",
    ])


def write_workspace(workspace: Path, scan: dict, mapping: dict) -> None:
    collision_data = collisions(scan, mapping)
    write_text(workspace / "README.md", readme_text(scan))
    write_text(workspace / "ledger.md", ledger_text(scan, mapping))
    write_text(workspace / "object-map.yaml", object_map_text(mapping))
    write_text(workspace / "collisions.yaml", collisions_text(collision_data))


def _ledger_status_counts(path: Path) -> dict[str, int]:
    counts = {"total": 0, "open": 0, "terminal": 0, "pending": 0, "deferred": 0}
    if not path.exists():
        return counts
    for raw in read_text(path).splitlines():
        if not raw.startswith("| ") or raw.startswith("| ---") or "Status" in raw:
            continue
        cells = [cell.strip().strip("`") for cell in raw.strip().strip("|").split("|")]
        if len(cells) < 5:
            continue
        status = cells[4]
        counts["total"] += 1
        if status in TERMINAL_STATUSES:
            counts["terminal"] += 1
        if status in OPEN_STATUSES:
            counts["open"] += 1
        if status == "pending":
            counts["pending"] += 1
        if status == "deferred":
            counts["deferred"] += 1
    return counts


def _collision_counts(path: Path) -> dict[str, int]:
    counts = {"id": 0, "path": 0, "ambiguous": 0}
    if not path.exists():
        return counts
    section = ""
    section_keys = {"id_collisions:": "id", "path_collisions:": "path", "ambiguous_matches:": "ambiguous"}
    for raw in read_text(path).splitlines():
        stripped = raw.strip()
        if stripped in section_keys:
            section = section_keys[stripped]
            continue
        if stripped == "- type: collision" and section:
            counts[section] += 1
    return counts


def _object_map_rows(path: Path) -> int:
    if not path.exists():
        return 0
    return len([line for line in read_text(path).splitlines() if line.startswith("  - source_id: ")])


def status(paths, slug: str) -> dict:
    existing = matches(paths, slug)
    workspace = existing[-1] if existing else None
    empty = {"total": 0, "open": 0, "terminal": 0, "pending": 0, "deferred": 0}
    counts = _ledger_status_counts(workspace / "ledger.md") if workspace else empty
    collision_counts = _collision_counts(workspace / "collisions.yaml") if workspace else {"id": 0, "path": 0, "ambiguous": 0}
    return {
        "schema": SOURCE_INTEGRATION_STATUS_SCHEMA,
        "slug": slug,
        "workspace": display_path(workspace, paths.root) if workspace else "",
        "workspace_found": workspace is not None,
        "existing_workspaces": [display_path(path, paths.root) for path in existing],
        "expected_files": EXPECTED_FILES,
        "missing_files": [name for name in EXPECTED_FILES if workspace and not (workspace / name).exists()] if workspace else EXPECTED_FILES,
        "progress": counts,
        "open_rows": counts["open"],
        "terminal_counts": {"terminal": counts["terminal"]},
        "collisions": collision_counts,
        "object_map_rows": _object_map_rows(workspace / "object-map.yaml") if workspace else 0,
        "notes": ["status reads the integration workspace only; it does not inspect or mutate the staged source tree"],
    }
