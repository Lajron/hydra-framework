"""Migration source discovery and slug validation."""

from __future__ import annotations

from pathlib import Path

from hydra_engine.identity.slugs import slugify
from hydra_engine.intake.paths import IntakePaths


def migration_source_name(path: Path) -> str:
    return slugify(path.name.removeprefix(".") or path.name)


def validate_migration_slug(slug: str) -> str:
    normalized = slugify(slug)
    if not normalized or normalized != slug or "/" in slug or "\\" in slug:
        raise ValueError(f"invalid migration slug `{slug}`; use a simple slug such as `legacy-ai`")
    return normalized


def iter_migration_source_roots(paths: IntakePaths, slug: str = "") -> list[Path]:
    root = paths.staging_root()
    if slug:
        source = root / slug
        return [source] if source.exists() else []
    if not root.is_dir():
        return []
    ignored = {"README.md", ".gitkeep"}
    return sorted(path for path in root.iterdir() if path.name not in ignored)
