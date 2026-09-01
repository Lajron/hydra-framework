"""What travels when this Hydra copy is seeded into a target repository."""

from __future__ import annotations

from pathlib import Path

INIT_SOURCES = ["AI_SYSTEM.md", "AGENTS.md", ".hydra-framework"]


def init_should_copy(rel: Path) -> bool:
    """Whether one repository-relative path travels with a Hydra copy.

    Framework definition travels; the source repository's own history does not.
    Task *templates* are definition, so they must travel even though the rest of
    `tasks/` must not.
    """
    if any(part in {"__pycache__", ".git"} for part in rel.parts):
        return False
    if rel.parts[:3] == (".hydra-framework", "tasks", "personal") and rel.name != ".gitkeep":
        return False
    return True


def planned_init_files(source_root: Path, target_root: Path) -> list[tuple[Path, Path]]:
    """Source-to-destination pairs for copying this framework into a target."""
    planned: list[tuple[Path, Path]] = []
    for name in INIT_SOURCES:
        source = source_root / name
        if not source.exists():
            continue
        if source.is_file():
            planned.append((source, target_root / name))
            continue
        for path in sorted(source.rglob("*")):
            if not path.is_file():
                continue
            rel = path.relative_to(source_root)
            if not init_should_copy(rel):
                continue
            planned.append((path, target_root / rel))
    return planned
