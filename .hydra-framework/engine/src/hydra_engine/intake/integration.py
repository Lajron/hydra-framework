"""Source integration inventory and workspace creation."""

from __future__ import annotations

import re
from pathlib import Path

from hydra_engine.documents.tokens import display_path, read_text, write_text
from hydra_engine.intake import integration_workspace
from hydra_engine.intake.inventory import migration_inventory
from hydra_engine.intake.staging import validate_migration_slug
from hydra_engine.objects.discovery import ObjectLocations, collect_hydra_objects
from hydra_engine.providers.paths import ProvidersPaths
from hydra_engine.providers.reclaim import classify_surfaces

SOURCE_INTEGRATION_SCAN_SCHEMA = "hydra-framework.source-integration-scan.v1"
SOURCE_OBJECT_MAP_SCHEMA = integration_workspace.SOURCE_OBJECT_MAP_SCHEMA


def integration_workspace_matches(paths, slug: str) -> list[Path]:
    return integration_workspace.matches(paths, slug)


def source_root(paths, slug: str) -> Path:
    return paths.staging_root() / validate_migration_slug(slug)


def source_hydra_root(paths, slug: str) -> Path:
    return source_root(paths, slug) / ".hydra-framework"


def source_object_locations(paths, slug: str) -> ObjectLocations:
    source = source_root(paths, slug)
    hydra = source / ".hydra-framework"
    return ObjectLocations(
        root=paths.root,
        hydra=hydra,
        local=source / ".hydra-framework.local",
        personal_tasks_rel="tasks/personal",
        object_registry=hydra / "cognition/graph/registry.yaml",
    )


def _source_display_path(slug: str, object_path: str) -> str:
    if object_path.startswith(".hydra-framework/"):
        return f".migrations/{slug}/{object_path}"
    if object_path.startswith(".hydra-framework.local/"):
        return f".migrations/{slug}/{object_path}"
    return object_path


def _as_map(value: object) -> dict:
    return value if isinstance(value, dict) else {}


def _as_str(value: object, fallback: str = "") -> str:
    return value if isinstance(value, str) else fallback


def _manifest_summary(paths, slug: str) -> tuple[dict, list[str]]:
    manifest_path = source_hydra_root(paths, slug) / "manifest.yaml"
    if not manifest_path.exists():
        return {}, []
    manifest: dict[str, object] = {}
    current_map = ""
    for raw in read_text(manifest_path).splitlines():
        if not raw.strip() or raw.strip().startswith("#"):
            continue
        if raw.startswith("  ") and current_map and ":" in raw:
            key, _, value = raw.strip().partition(":")
            child = _as_map(manifest.setdefault(current_map, {}))
            child[key.strip()] = value.strip().strip("'\"")
            manifest[current_map] = child
            continue
        current_map = ""
        if ":" not in raw:
            continue
        key, _, value = raw.partition(":")
        key = key.strip()
        value = value.strip()
        if value:
            manifest[key] = value.strip("'\"")
        else:
            manifest[key] = {}
            current_map = key
    return manifest, []


def _project_name(manifest: dict, slug: str) -> str:
    lineage = _as_map(manifest.get("lineage"))
    return _as_str(lineage.get("adopted_into")) or _as_str(manifest.get("project_name")) or _as_str(manifest.get("framework_name")) or slug


def _count_existing_dirs(path: Path) -> int:
    return len([item for item in path.iterdir() if item.is_dir()]) if path.is_dir() else 0


def _inactive_task_records(paths, slug: str) -> list[str]:
    tasks_root = source_hydra_root(paths, slug) / "tasks/personal"
    if not tasks_root.is_dir():
        return []
    inactive: list[str] = []
    for path in sorted(tasks_root.rglob("*.md")):
        text = read_text(path)
        if re.search(r"^Status:\s*inactive\s*$", text, flags=re.MULTILINE | re.IGNORECASE):
            inactive.append(display_path(path, paths.root))
    return inactive


def _risk_counts(inventory: dict) -> dict[str, int]:
    risks: dict[str, int] = {}
    for source in inventory.get("sources", []):
        classifications = source.get("classifications", {})
        if not isinstance(classifications, dict):
            continue
        for tag, count in classifications.items():
            if tag in {"credential-or-private-risk", "machine-local-risk", "private-hydra-risk"}:
                risks[str(tag)] = risks.get(str(tag), 0) + int(count)
    return dict(sorted(risks.items()))


def _source_objects(paths, slug: str) -> tuple[list[dict], list[str]]:
    hydra = source_hydra_root(paths, slug)
    if not hydra.is_dir():
        return [], []
    return collect_hydra_objects(source_object_locations(paths, slug))


def _local_objects(local_locations: ObjectLocations | None) -> tuple[list[dict], list[str]]:
    if local_locations is None:
        return [], []
    return collect_hydra_objects(local_locations)


def _object_totals(objects: list[dict]) -> dict[str, int]:
    totals: dict[str, int] = {}
    for obj in objects:
        key = str(obj["family"]).lower().replace("/", "-").replace(" ", "-")
        totals[key] = totals.get(key, 0) + 1
    return dict(sorted(totals.items()))


def _surface_counts(paths, slug: str) -> dict[str, int]:
    source = source_root(paths, slug)
    hydra = source / ".hydra-framework"
    counts: dict[str, int] = {}
    for item in classify_surfaces(ProvidersPaths(root=source, hydra=hydra)):
        status = item["status"]
        counts[status] = counts.get(status, 0) + 1
    return dict(sorted(counts.items()))


def _path_collisions(source_objects: list[dict], local_objects: list[dict], slug: str) -> list[dict]:
    local_by_path = {obj["path"]: obj for obj in local_objects}
    collisions = []
    for obj in source_objects:
        local = local_by_path.get(obj["path"])
        if local:
            collisions.append({
                "source_original_id": obj["id"],
                "source_path": _source_display_path(slug, obj["path"]),
                "local_id": local["id"],
                "local_path": local["path"],
            })
    return collisions


def _id_collisions(source_objects: list[dict], local_objects: list[dict]) -> list[dict]:
    local_by_id = {obj["id"]: obj for obj in local_objects}
    collisions = []
    for obj in source_objects:
        local = local_by_id.get(obj["id"])
        if local:
            collisions.append({
                "source_original_id": obj["id"],
                "local_id": local["id"],
                "local_path": local["path"],
            })
    return collisions


def integration_scan(paths, slug: str, local_locations: ObjectLocations | None = None) -> dict:
    slug = validate_migration_slug(slug)
    inventory = migration_inventory(paths, slug)
    source = source_root(paths, slug)
    hydra = source / ".hydra-framework"
    manifest, manifest_errors = _manifest_summary(paths, slug)
    source_objects, source_errors = _source_objects(paths, slug)
    local_objects, local_errors = _local_objects(local_locations)
    lineage = _as_map(manifest.get("lineage"))
    id_collisions = _id_collisions(source_objects, local_objects)
    path_collisions = _path_collisions(source_objects, local_objects, slug)
    existing = integration_workspace_matches(paths, slug)

    notes = [
        "read-only scan; staged source material and source Hydra tree are not modified",
        "source integration rows are object/capability decisions, not migration file-drain rows",
    ]
    notes.extend(inventory.get("notes", []))
    notes.extend(manifest_errors)
    if source_errors:
        notes.extend(f"source object discovery: {error}" for error in source_errors)
    if local_errors:
        notes.extend(f"local object discovery: {error}" for error in local_errors)
    if source.exists() and not hydra.is_dir():
        notes.append(f"staged source has no Hydra tree at .migrations/{slug}/.hydra-framework")

    inactive_tasks = _inactive_task_records(paths, slug)
    return {
        "schema": SOURCE_INTEGRATION_SCAN_SCHEMA,
        "slug": slug,
        "source_found": source.exists(),
        "source_path": display_path(source, paths.root) if source.exists() else "",
        "hydra_found": hydra.is_dir(),
        "project_name": _project_name(manifest, slug),
        "seed_version": _as_str(manifest.get("seed_version"), "unknown"),
        "lineage": lineage,
        "manifest": {
            "path": display_path(hydra / "manifest.yaml", paths.root),
            "found": bool(manifest),
        },
        "objects": {
            "total": len(source_objects),
            "by_family": _object_totals(source_objects),
        },
        "capabilities": len([obj for obj in source_objects if obj["family"] == "Capability"]),
        "knowledge_packages": len([obj for obj in source_objects if obj["kind"] == "knowledge-package"]),
        "migrations": {
            "workspaces": _count_existing_dirs(hydra / "intake/migrations"),
            "staged_sources": _count_existing_dirs(source / ".migrations"),
        },
        "generated_surfaces": _surface_counts(paths, slug),
        "foreign_task_records": {
            "inactive": len(inactive_tasks),
            "paths": inactive_tasks,
        },
        "private_material_risk": _risk_counts(inventory),
        "id_collisions": id_collisions,
        "path_collisions": path_collisions,
        "existing_workspaces": [display_path(path, paths.root) for path in existing],
        "planned_workspace": integration_workspace.planned_display_path(paths, slug),
        "inventory": inventory,
        "notes": notes,
    }


def _last_id_segment(hydra_id: str) -> str:
    return hydra_id.rstrip("/").rsplit("/", 1)[-1]


def _slug_part(value: str, fallback: str) -> str:
    cleaned = re.sub(r"[^a-z0-9-]+", "-", value.lower()).strip("-")
    cleaned = re.sub(r"-+", "-", cleaned)
    return cleaned or fallback


def _source_scoped_ids(source_objects: list[dict], slug: str) -> dict[tuple[str, str], str]:
    used: dict[str, int] = {}
    scoped: dict[tuple[str, str], str] = {}
    for obj in sorted(source_objects, key=lambda item: (item["kind"], item["path"], item["id"])):
        kind = _slug_part(str(obj["kind"]), "object")
        name = _slug_part(_last_id_segment(str(obj["id"])) or Path(str(obj["path"])).stem or str(obj["title"]), "object")
        base = f"hydra://source/{slug}/{kind}/{name}"
        count = used.get(base, 0) + 1
        used[base] = count
        scoped[(obj["id"], obj["path"])] = base if count == 1 else f"{base}-{count}"
    return scoped


def _normalize_title(title: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", title.lower()).strip()


def _index(objects: list[dict], key) -> dict[str, list[dict]]:
    result: dict[str, list[dict]] = {}
    for obj in objects:
        value = key(obj)
        if value:
            result.setdefault(value, []).append(obj)
    return result


def _match_source_object(obj: dict, indexes: dict[str, dict[str, list[dict]]]) -> tuple[str, dict | None, int]:
    checks = (
        ("uid", obj["uid"]),
        ("path", obj["path"]),
        ("digest", obj["digest"]),
        ("title", _normalize_title(str(obj["title"]))),
    )
    for method, value in checks:
        if not value:
            continue
        matches = indexes[method].get(str(value), [])
        if len(matches) == 1:
            return method, matches[0], 1
        if len(matches) > 1:
            return f"ambiguous-{method}", None, len(matches)
    return "none", None, 0


def integration_object_map(paths, slug: str, local_locations: ObjectLocations | None = None) -> dict:
    slug = validate_migration_slug(slug)
    source_objects, source_errors = _source_objects(paths, slug)
    if source_errors:
        raise ValueError("; ".join(source_errors))
    local_objects, local_errors = _local_objects(local_locations)
    if local_errors:
        raise ValueError("; ".join(local_errors))
    scoped_ids = _source_scoped_ids(source_objects, slug)
    indexes = {
        "uid": _index(local_objects, lambda item: item["uid"]),
        "path": _index(local_objects, lambda item: item["path"]),
        "digest": _index(local_objects, lambda item: item["digest"]),
        "title": _index(local_objects, lambda item: _normalize_title(str(item["title"]))),
    }
    rows = []
    for obj in sorted(source_objects, key=lambda item: scoped_ids[(item["id"], item["path"])]):
        method, local, match_count = _match_source_object(obj, indexes)
        rows.append({
            "source_id": scoped_ids[(obj["id"], obj["path"])],
            "original_id": obj["id"],
            "uid": obj["uid"],
            "kind": obj["kind"],
            "family": obj["family"],
            "title": obj["title"],
            "source_path": _source_display_path(slug, obj["path"]),
            "source_envelope_path": _source_display_path(slug, obj["envelope_path"]),
            "digest": obj["digest"],
            "match_method": method,
            "match_count": match_count,
            "local_id": local["id"] if local else "",
            "local_path": local["path"] if local else "",
            "verdict": "link" if local else "import",
            "status": "pending",
        })
    return {
        "schema": SOURCE_OBJECT_MAP_SCHEMA,
        "slug": slug,
        "source_path": display_path(source_root(paths, slug), paths.root),
        "created": integration_workspace.created_date(),
        "objects": rows,
    }


def create_integration_workspace(paths, slug: str, local_locations: ObjectLocations | None = None) -> dict:
    scan = integration_scan(paths, slug, local_locations)
    if not scan["source_found"]:
        raise ValueError(f"no staged source found at .migrations/{scan['slug']}")
    if not scan["hydra_found"]:
        raise ValueError(f"no staged Hydra source found at .migrations/{scan['slug']}/.hydra-framework")
    if scan["existing_workspaces"]:
        raise FileExistsError(
            f"source integration workspace already exists for `{scan['slug']}`: {', '.join(scan['existing_workspaces'])}"
        )
    mapping = integration_object_map(paths, scan["slug"], local_locations)
    workspace = paths.integration_workspace_root() / f"{mapping['created']}-{scan['slug']}"
    if workspace.exists():
        raise FileExistsError(f"source integration workspace already exists: {display_path(workspace, paths.root)}")
    integration_workspace.write_workspace(workspace, scan, mapping)
    scan["created_workspace"] = display_path(workspace, paths.root)
    scan["existing_workspaces"] = [display_path(workspace, paths.root)]
    return scan


def write_integration_object_map(paths, slug: str, local_locations: ObjectLocations | None = None) -> dict:
    slug = validate_migration_slug(slug)
    existing = integration_workspace_matches(paths, slug)
    if not existing:
        raise ValueError(f"no source integration workspace for `{slug}`; run `hydra.py integrate map {slug} --create` first")
    mapping = integration_object_map(paths, slug, local_locations)
    target = existing[-1] / "object-map.yaml"
    write_text(target, integration_workspace.object_map_text(mapping))
    return {
        "schema": SOURCE_OBJECT_MAP_SCHEMA,
        "slug": slug,
        "workspace": display_path(existing[-1], paths.root),
        "object_map": display_path(target, paths.root),
        "objects": len(mapping["objects"]),
    }

def integration_status(paths, slug: str) -> dict:
    return integration_workspace.status(paths, validate_migration_slug(slug))
