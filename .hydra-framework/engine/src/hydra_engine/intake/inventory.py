"""Migration staging inventory."""

from __future__ import annotations

from hydra_engine.documents.tokens import display_path
from hydra_engine.intake.classification import classify_migration_file
from hydra_engine.intake.paths import IntakePaths
from hydra_engine.intake.staging import iter_migration_source_roots, migration_source_name, validate_migration_slug
from hydra_engine.ports import git as git_port

MIGRATION_INVENTORY_SCHEMA = "hydra-framework.migration-inventory.v1"


def migration_inventory(paths: IntakePaths, slug: str = "") -> dict:
    if slug:
        slug = validate_migration_slug(slug)
    root = paths.staging_root()
    inventory = {
        "schema": MIGRATION_INVENTORY_SCHEMA,
        "staging_root": display_path(root, paths.root),
        "exists": root.is_dir(),
        "scope": slug or "all",
        "sources": [],
        "totals": {"sources": 0, "files": 0, "directories": 0, "bytes": 0},
        "notes": [
            "read-only inventory; staged material is source material, not canonical Hydra state",
            "keep private or never-tracked material under .hydra-framework.local/migrations/<slug>/originals/",
        ],
    }
    if not root.exists():
        inventory["notes"].append("create .migrations/ for already-shared material before running inventory")
        return inventory
    if not root.is_dir():
        inventory["notes"].append(".migrations exists but is not a directory")
        return inventory

    tracked = set(git_port.tracked_files(paths.root, ".migrations"))
    for source in iter_migration_source_roots(paths, slug):
        source_files = [source] if source.is_file() else sorted(path for path in source.rglob("*") if path.is_file())
        source_dirs = [] if source.is_file() else sorted(path for path in source.rglob("*") if path.is_dir())
        source_item = {
            "slug": migration_source_name(source),
            "path": display_path(source, paths.root),
            "files": len(source_files),
            "directories": len(source_dirs),
            "bytes": 0,
            "classifications": {},
            "findings": [],
            "tracked_files": 0,
            "untracked_files": 0,
        }
        for file_path in source_files:
            try:
                size = file_path.stat().st_size
            except OSError:
                size = 0
            source_item["bytes"] += size
            rel = display_path(file_path, paths.root)
            if rel in tracked:
                source_item["tracked_files"] += 1
            else:
                source_item["untracked_files"] += 1
            tags = classify_migration_file(file_path, source if source.is_dir() else source.parent)
            for tag in tags:
                source_item["classifications"][tag] = source_item["classifications"].get(tag, 0) + 1
            source_item["findings"].append({"path": rel, "bytes": size, "classifications": tags})
        source_item["classifications"] = dict(sorted(source_item["classifications"].items()))
        source_item["findings"].sort(key=lambda item: item["path"])
        inventory["sources"].append(source_item)
        inventory["totals"]["files"] += source_item["files"]
        inventory["totals"]["directories"] += source_item["directories"]
        inventory["totals"]["bytes"] += source_item["bytes"]
    inventory["totals"]["sources"] = len(inventory["sources"])
    if slug and not inventory["sources"]:
        inventory["notes"].append(f"no staged source found at .migrations/{slug}")
    return inventory
