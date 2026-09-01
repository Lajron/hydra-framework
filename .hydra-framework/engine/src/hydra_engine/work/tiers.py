"""State-tier boundaries.

The three tiers (placement rules):

    shared    describes the repository        .hydra-framework/          tracked
    personal  my structured in-flight work    tasks/personal/<owner>/    tracked
    private   my thinking, not permanent      .hydra-framework.local/    ignored
"""

from __future__ import annotations

import re
from pathlib import Path

from hydra_engine.documents.markdown import iter_markdown_files
from hydra_engine.documents.tokens import display_path, is_relative_to, read_text
from hydra_engine.finding import Finding
from hydra_engine.installation.private_tier import PRIVATE_TIER_SEED
from hydra_engine.ports import git as git_port
from hydra_engine.work.paths import WorkPaths

# Directories that leave the shared tree entirely, as (shared path, private
# path) pairs. Both are relative to their tier root and resolved at call time:
# baking the root paths in here would freeze them at import, which breaks
# relocating them and hides the coupling.
PRIVATE_TIER_MOVES = [
    ("intake/raw", "intake/raw"),
    ("intake/extracted", "intake/extracted"),
    ("intake/triage", "intake/triage"),
    ("repo/pending", "notes"),
    ("evolution/experiments", "evolution/experiments"),
]

# Task state that stops being a separate shared directory. Active records and
# checkpoints move under their owner; finished ones are deleted, because Git
# already owns them and a second copy is the thing placement rules forbid.
TASK_TIER_MOVES = ["tasks/active", "tasks/checkpoints"]
TASK_TIER_DELETES = ["tasks/completed", "tasks/archive"]

# Private areas holding one person's *work*. A shared file citing a specific file
# in one of these is depending on material nobody else has.
#
# The other private areas -- `monitoring/`, `developer/`, `machine/`, `secrets/`,
# `repo-overrides/` -- are conventional locations with fixed names that everyone
# has their own copy of. Naming `monitoring/token-hooks.json` tells a reader
# where to put theirs; it does not cite yours.
PRIVATE_CONTENT_AREAS = "intake|notes|tasks|migrations|evolution|scratch|logs"

# A concrete file: real extension, no `<placeholder>` segment. Naming a directory
# in prose is normal and fine.
PRIVATE_FILE_REF_RE = re.compile(
    r"\.hydra-framework\.local/(?:" + PRIVATE_CONTENT_AREAS + r")/"
    r"(?![^\s`)\]]*<)[^\s`)\]]+\.[A-Za-z0-9]{1,5}\b"
)

TASK_PRIVATE_REF_FIELDS = (
    "- Required dependencies, services, generated artifacts, or private local requirements:",
    "- Running state:",
    "- Resume check:",
)


def private_tier_moves(paths: WorkPaths) -> list[tuple[Path, Path]]:
    return [(paths.hydra / shared, paths.local / private) for shared, private in PRIVATE_TIER_MOVES]


def validate_tier_boundaries(paths: WorkPaths) -> list[Finding]:
    """Keep the three tiers from leaking into each other.

    Two failures matter, and both are silent without a check.

    A private file tracked in Git is the model failing outright: material that
    was written on the assumption it stays local becomes permanent and citable.

    A shared file linking into a private path is worse than a broken link,
    because it reads as a real citation. Whoever wrote it can follow it; nobody
    else can, and the reader has no way to tell the difference. This is why a
    promotion record must contain what it needs rather than pointing at the
    private descriptor it came from.
    """
    findings: list[Finding] = []

    for path in git_port.tracked_files(paths.root, ".hydra-framework.local"):
        findings.append(Finding(
            path=path, code="tier-boundaries",
            detail=f"{path}: private-tier file is tracked in Git; it must be ignored",
        ))

    for source, destination in private_tier_moves(paths):
        if source.is_dir() and any(p.is_file() and p.name != ".gitkeep" for p in source.rglob("*")):
            rel = source.relative_to(paths.hydra).as_posix()
            findings.append(Finding(
                path=f".hydra-framework/{rel}", code="tier-boundaries",
                detail=(
                    f".hydra-framework/{rel}: private-tier content in the shared tree; "
                    f"run `hydra.py migrate-state` to move it to {display_path(destination, paths.root)}"
                ),
            ))
    for rel in TASK_TIER_MOVES + TASK_TIER_DELETES:
        source = paths.hydra / rel
        if source.is_dir() and any(source.glob("*.md")):
            findings.append(Finding(
                path=f".hydra-framework/{rel}", code="tier-boundaries",
                detail=(
                    f".hydra-framework/{rel}: superseded task directory still holds records; "
                    "run `hydra.py migrate-state`"
                ),
            ))

    for path in iter_markdown_files(paths.hydra):
        for line in read_text(path).splitlines():
            match = PRIVATE_FILE_REF_RE.search(line)
            if not match or private_ref_allowed_in_task_record(path, paths, line):
                continue
            findings.append(Finding(
                path=display_path(path, paths.root), code="tier-boundaries",
                detail=(
                    f"{display_path(path, paths.root)}: cites private file `{match.group(0)}`, "
                    "which no teammate can read; inline what it needs instead"
                ),
            ))
            break

    return findings


def private_ref_allowed_in_task_record(path: Path, paths: WorkPaths, line: str) -> bool:
    """Allow resumability fields to name required private local state."""
    if not is_relative_to(path, paths.personal_tasks_root()):
        return False
    stripped = line.strip()
    return any(stripped.startswith(field) for field in TASK_PRIVATE_REF_FIELDS)


def validate_private_tier_documented(paths: WorkPaths) -> list[Finding]:
    """Every code-seeded private area must appear in the shared shape doc."""
    doc = paths.hydra / "repo/knowledge/state-tiers.md"
    if not doc.exists():
        return [Finding(
            path=display_path(doc, paths.root),
            code="private-tier-shape",
            detail=f"{display_path(doc, paths.root)}: missing private tier shape document",
        )]

    text = read_text(doc)
    findings: list[Finding] = []
    for area in PRIVATE_TIER_SEED:
        expected = f"`{area.path}/`"
        if expected not in text:
            findings.append(Finding(
                path=display_path(doc, paths.root),
                code="private-tier-shape",
                detail=f"{display_path(doc, paths.root)}: missing seeded private area {expected}",
            ))
    return findings
