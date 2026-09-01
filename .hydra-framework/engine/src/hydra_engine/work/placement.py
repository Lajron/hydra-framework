"""Write-time tier-placement notices.

`hydra.py` no longer keeps a `tier_placement_notice` delegator: `providers`
finished the other half `command_hook_post_edit` needed
(`classify_surfaces`), so that command moved to
`hydra_engine.commands.hooks` in full and calls this function directly.
"""

from __future__ import annotations

from pathlib import Path

from hydra_engine.documents.tokens import is_relative_to
from hydra_engine.work.owners import HydraOwnerError, resolve_owner
from hydra_engine.work.paths import WorkPaths
from hydra_engine.work.tiers import PRIVATE_TIER_MOVES, TASK_TIER_DELETES, TASK_TIER_MOVES


def tier_placement_notice(edited: Path, paths: WorkPaths, env_owner: str, git_email: str) -> list[str]:
    """Advisory lines when a write lands in the wrong state tier.

    Same mechanism that keeps provider directories from becoming sources of
    truth, applied to the tier boundary: catch it at write time, when moving the
    file is still free, rather than at review time when it is already shared.
    Guidance only; it never blocks the write.
    """
    if not is_relative_to(edited, paths.root):
        return []
    rel = edited.relative_to(paths.root).as_posix()

    for shared, private in PRIVATE_TIER_MOVES:
        if rel.startswith(f".hydra-framework/{shared}/"):
            return [
                f"Hydra: `{rel}` is private-tier state written into the shared tree.",
                f"  It belongs in `.hydra-framework.local/{private}/`, which is not tracked.",
                "  Shared state describes the repository; this describes your thinking.",
            ]
    for path in TASK_TIER_MOVES + TASK_TIER_DELETES:
        if rel.startswith(f".hydra-framework/{path}/"):
            return [
                f"Hydra: `{rel}` uses a retired task directory.",
                "  Active records live in `.hydra-framework/tasks/personal/<owner>/`.",
                "  Finished ones are deleted; Git history is the archive.",
                "  Mechanical path: `hydra.py migrate-state --apply`.",
            ]

    if rel.startswith(".hydra-framework/tasks/personal/"):
        parts = Path(rel).relative_to(".hydra-framework/tasks/personal").parts
        try:
            owner = resolve_owner("", env_owner, git_email)
        except HydraOwnerError:
            return []
        if len(parts) > 1 and parts[0] != owner:
            return [
                f"Hydra: `{rel}` is {parts[0]}'s task record, and you are {owner}.",
                "  Read it freely; editing someone else's record is how two people",
                "  end up believing different things about the same work.",
                f"  To take it over: `hydra.py task handoff {rel} --to {owner}`.",
            ]
    return []
