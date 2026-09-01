"""Board rendering and per-prompt state pointers."""

from __future__ import annotations

import datetime as _dt
import re
from pathlib import Path

from hydra_engine.ports import clock
from hydra_engine.work import task_store
from hydra_engine.work.owners import HydraOwnerError, resolve_owner
from hydra_engine.work.paths import WorkPaths
from hydra_engine.work.task_records import (
    iter_personal_checkpoints,
    iter_personal_task_files,
    task_name_from_path,
    task_summary,
)

STATE_POINTER_TASK_NAME_LIMIT = 3


def _stale_before(stale_days: int | None) -> str | None:
    if stale_days is None:
        return None
    return (_dt.date.fromisoformat(clock.today()) - _dt.timedelta(days=stale_days)).isoformat()


def _passes_filters(summary: dict[str, str], blocked_only: bool, stale_before: str | None) -> bool:
    if blocked_only and summary["status"] != "blocked":
        return False
    if stale_before is not None:
        updated = summary["updated"]
        if not (updated and updated < stale_before):
            return False
    return True


def board_rows(
    paths: WorkPaths,
    owner_filter: str | None = None,
    blocked_only: bool = False,
    stale_days: int | None = None,
) -> list[dict[str, str]]:
    """Who is working on what, computed from the records themselves (or an
    up-to-date store built from them -- the store's freshness contract
    makes the two indistinguishable in output).

    Nothing is authored here. A status file would be a second index that can
    disagree with the records it summarizes; the records are the only
    authority and this view cannot drift from them.
    """
    stale_before = _stale_before(stale_days)

    conn = task_store.open_fresh_task_store(paths)
    if conn is not None:
        try:
            return task_store.board_rows_from_store(conn, owner_filter, blocked_only, stale_before)
        finally:
            conn.close()

    tasks = iter_personal_task_files(paths)
    if owner_filter:
        tasks = [path for path in tasks if path.parent.name == owner_filter]
    summaries = [task_summary(path, paths.root) for path in tasks]
    return [summary for summary in summaries if _passes_filters(summary, blocked_only, stale_before)]


def checkpoint_counts_by_owner(paths: WorkPaths) -> dict[str, int]:
    counts: dict[str, int] = {}
    for path in iter_personal_checkpoints(paths):
        counts[path.parent.parent.name] = counts.get(path.parent.parent.name, 0) + 1
    return counts


def reflection_packet_count(reflections_dir: Path) -> int:
    if not reflections_dir.is_dir():
        return 0
    return sum(1 for path in reflections_dir.glob("*.md") if path.name != "README.md")


_TELEMETRY_EVIDENCE_STATUS_RE = re.compile(r"(?m)^status:\s*(\S+)\s*$")


def telemetry_evidence_open_count(packages_dir: Path) -> int:
    """Open packages only -- an absorbed, superseded, or rejected package
    already answered the question a pointer line would raise, the same way
    a terminal candidate does not count toward `evolution/candidates/`'s
    own (absent) depth signal. A lightweight regex read of the envelope's
    `status:` line, not a full YAML parse: this runs on every prompt."""
    if not packages_dir.is_dir():
        return 0
    count = 0
    for package_dir in packages_dir.iterdir():
        overview = package_dir / "overview.md"
        if not overview.is_file():
            continue
        match = _TELEMETRY_EVIDENCE_STATUS_RE.search(overview.read_text(encoding="utf-8"))
        if match and match.group(1).strip().lower() == "open":
            count += 1
    return count


def state_pointer_lines(
    paths: WorkPaths,
    env_owner: str,
    git_email: str,
    reflections_dir: Path,
    telemetry_packages_dir: Path | None = None,
) -> list[str]:
    """Pointers and counts for the state tiers. Never contents.

    This runs on every prompt, so it is bounded hard: counts computed from a
    glob, at most a few lines, and silent when there is nothing in flight. An
    agent must be able to learn what its owner is working on without being told,
    but that cannot become a per-prompt dump of records.
    """
    try:
        owner = resolve_owner("", env_owner, git_email)
    except HydraOwnerError:
        return []

    all_tasks = iter_personal_task_files(paths)
    mine = [path for path in all_tasks if path.parent.name == owner]
    others = len(all_tasks) - len(mine)
    reflections = reflection_packet_count(reflections_dir)
    telemetry_open = telemetry_evidence_open_count(telemetry_packages_dir) if telemetry_packages_dir else 0
    if not mine and not others and not reflections and not telemetry_open:
        return []

    lines = ["Hydra state (pointers only):"]
    if mine:
        names = ", ".join(task_name_from_path(path) for path in mine[:STATE_POINTER_TASK_NAME_LIMIT])
        more = f", +{len(mine) - STATE_POINTER_TASK_NAME_LIMIT} more" if len(mine) > STATE_POINTER_TASK_NAME_LIMIT else ""
        lines.append(f"- Yours ({owner}): {len(mine)} active — {names}{more}. See `hydra.py board --owner {owner}`.")
    if others:
        lines.append(f"- Teammates: {others} active record(s). `hydra.py board`. Read, do not edit.")
    if reflections:
        lines.append(f"- Reflections: {reflections} pending in `evolution/reflections/`. `hydra.py validate` notes stale ones.")
    if telemetry_open:
        lines.append(f"- Telemetry evidence: {telemetry_open} open in `repo/telemetry/packages/`. `hydra.py validate` notes stale ones.")
    lines.append("- Private scratch: `.hydra-framework.local/` — yours, untracked, never authoritative for the team.")
    return lines
