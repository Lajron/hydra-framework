"""Pre-0007 state migration planning."""

from __future__ import annotations

from pathlib import Path

from hydra_engine.documents.tokens import display_path, read_text
from hydra_engine.identity.slugs import slugify
from hydra_engine.ports import git as git_port
from hydra_engine.work.owners import resolve_owner
from hydra_engine.work.paths import WorkPaths
from hydra_engine.work.task_records import task_header_field
from hydra_engine.work.tiers import TASK_TIER_DELETES, TASK_TIER_MOVES, private_tier_moves


def owner_for_migrated_record(
    text: str, source: Path, path: Path, is_checkpoint: bool, env_owner: str, git_email: str
) -> str:
    """Who a pre-0007 record belongs to.

    Records carry `Owner:`; checkpoints do not, so they inherit from the task
    they name. Anything still unattributed falls to whoever runs the migration --
    correct in the seed, and correct in a downstream copy where the person
    migrating is the person whose state it is.

    `slugify` is not usable directly here: it returns the literal `task` for
    empty input, which would silently invent an owner named "task".
    """
    owner = (task_header_field(text, "Owner") or "").strip()
    if not owner and is_checkpoint:
        named = (task_header_field(text, "Task") or "").strip()
        if named:
            candidate = source.parent / "active" / Path(named).name
            if candidate.exists():
                owner = (task_header_field(read_text(candidate), "Owner") or "").strip()
    if not owner or owner.lower() == "unassigned":
        return resolve_owner("", env_owner, git_email)
    return slugify(owner)


def plan_state_migration(
    paths: WorkPaths, env_owner: str, git_email: str
) -> dict[str, list[tuple[Path, Path | None]]]:
    """What `migrate-state` would do, without doing it.

    Same plan in the seed and in every downstream copy, so the migration happens
    identically everywhere instead of being reinterpreted from a doc twice.
    """
    plan: dict[str, list[tuple[Path, Path | None]]] = {
        "move": [],
        "delete": [],
        "drop": [],
        "retire": [],
    }

    for source, destination in private_tier_moves(paths):
        if not source.is_dir():
            continue
        for path in sorted(source.rglob("*")):
            if not path.is_file() or path.name == ".gitkeep":
                continue
            # A directory README documents the shared tier it sits in. The
            # private tier has its own shape in `repo/knowledge/state-tiers.md`.
            if path.name == "README.md":
                plan["drop"].append((path, None))
            else:
                plan["move"].append((path, destination / path.relative_to(source)))

    for rel in TASK_TIER_MOVES:
        source = paths.hydra / rel
        if not source.is_dir():
            continue
        is_checkpoints = Path(rel).name == "checkpoints"
        for path in sorted(source.glob("*.md")):
            owner = owner_for_migrated_record(read_text(path), source, path, is_checkpoints, env_owner, git_email)
            destination = paths.owner_task_dir(owner)
            if is_checkpoints:
                destination = destination / "checkpoints"
            plan["move"].append((path, destination / path.name))

    # Finished records are removed because Git already holds them. Where Git does
    # not -- uncommitted work -- the working copy is the only copy, so it is
    # retired to private staging instead, the same rule established for
    # migrated material.
    for rel in TASK_TIER_DELETES:
        source = paths.hydra / rel
        if not source.is_dir():
            continue
        for path in sorted(source.glob("*.md")):
            if git_port.tracked_files(paths.root, display_path(path, paths.root)):
                plan["delete"].append((path, None))
            else:
                # `completed/` and `archive/` hold the same filename for the same
                # task, so retiring both into one flat directory would overwrite
                # one with the other.
                plan["retire"].append((path, paths.retired_tasks_root() / source.name / path.name))

    return plan


def migration_destination_conflicts(
    moves: list[tuple[Path, Path | None]], paths: WorkPaths
) -> list[str]:
    """Find migration writes that would overwrite or collapse distinct sources."""
    conflicts: list[str] = []
    seen: dict[str, Path] = {}
    for source, destination in moves:
        if destination is None:
            continue
        key = destination.as_posix()
        if destination.exists():
            conflicts.append(f"{display_path(source, paths.root)} -> {display_path(destination, paths.root)} already exists")
        if key in seen:
            conflicts.append(
                f"{display_path(source, paths.root)} and {display_path(seen[key], paths.root)} both target {display_path(destination, paths.root)}"
            )
        seen[key] = source
    return conflicts


def remove_empty_state_dir(path: Path) -> None:
    """Drop a state directory once its contents have moved.

    `.gitkeep` files are removed with it: they exist to keep an empty directory
    in Git, and these directories are no longer supposed to be in Git at all.
    """
    if not path.is_dir():
        return
    for leftover in sorted(path.rglob("*"), reverse=True):
        if leftover.name == ".gitkeep":
            leftover.unlink()
        elif leftover.is_dir() and not any(leftover.iterdir()):
            leftover.rmdir()
    if not any(path.iterdir()):
        path.rmdir()


def cleanup_after_apply(paths: WorkPaths) -> None:
    """Drop every source-side state directory a completed `--apply` emptied."""
    for source, _ in private_tier_moves(paths):
        remove_empty_state_dir(source)
    for rel in TASK_TIER_MOVES + TASK_TIER_DELETES:
        remove_empty_state_dir(paths.hydra / rel)
