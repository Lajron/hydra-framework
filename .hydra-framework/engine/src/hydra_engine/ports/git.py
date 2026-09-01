"""Git port.

The sole source of git-derived state: config values and tracked-file
listings. Parameterized by `root` instead of a module global, so a golden
fixture points these at a fixture tree the same way `RepoContext` does for
the rest of command dispatch.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

GIT_CONFIG_TIMEOUT_SECONDS = 5
GIT_ADD_TIMEOUT_SECONDS = 15
GIT_DIFF_TIMEOUT_SECONDS = 15
GIT_LOG_TIMEOUT_SECONDS = 15
GIT_LS_FILES_TIMEOUT_SECONDS = 15
GIT_CHECK_IGNORE_TIMEOUT_SECONDS = 15
GIT_STATUS_TIMEOUT_SECONDS = 15


def config_email(root: Path) -> str:
    try:
        result = subprocess.run(
            ["git", "config", "user.email"],
            cwd=str(root),
            capture_output=True,
            text=True,
            timeout=GIT_CONFIG_TIMEOUT_SECONDS,
        )
    except (OSError, subprocess.SubprocessError):
        return ""
    return result.stdout.strip() if result.returncode == 0 else ""


def last_commit_iso(root: Path, path: str) -> str:
    """The ISO-8601 commit date of the last commit touching `path`, or `""`
    when git is absent, the path is untracked, or the call fails. Never
    raises: staleness is a warning-level convenience, not something that
    should ever break a caller."""
    try:
        result = subprocess.run(
            ["git", "log", "-1", "--format=%cI", "--", path],
            cwd=str(root),
            capture_output=True,
            text=True,
            timeout=GIT_LOG_TIMEOUT_SECONDS,
        )
    except (OSError, subprocess.SubprocessError):
        return ""
    if result.returncode != 0:
        return ""
    return result.stdout.strip()


def tracked_files(root: Path, prefix: str) -> list[str]:
    try:
        result = subprocess.run(
            ["git", "ls-files", "--", prefix],
            cwd=str(root),
            capture_output=True,
            text=True,
            timeout=GIT_LS_FILES_TIMEOUT_SECONDS,
        )
    except (OSError, subprocess.SubprocessError):
        return []
    if result.returncode != 0:
        return []
    return [line for line in result.stdout.splitlines() if line.strip()]


def ignore_match(root: Path, path: str) -> str:
    """Verbose `git check-ignore` match for `path`, or `""` when not ignored.

    The verbose line is useful evidence for migration/takeover routing, but a
    missing Git repository or a non-ignored path is not an error for callers.
    """
    try:
        result = subprocess.run(
            ["git", "check-ignore", "-v", "--", path],
            cwd=str(root),
            capture_output=True,
            text=True,
            timeout=GIT_CHECK_IGNORE_TIMEOUT_SECONDS,
        )
    except (OSError, subprocess.SubprocessError):
        return ""
    return result.stdout.strip() if result.returncode == 0 else ""


def stage_file(root: Path, path: str) -> bool:
    try:
        result = subprocess.run(
            ["git", "add", "--", path],
            cwd=str(root),
            capture_output=True,
            text=True,
            timeout=GIT_ADD_TIMEOUT_SECONDS,
        )
    except (OSError, subprocess.SubprocessError):
        return False
    return result.returncode == 0


def is_tracked(root: Path, path: str) -> bool:
    try:
        result = subprocess.run(
            ["git", "ls-files", "--error-unmatch", "--", path],
            cwd=str(root),
            capture_output=True,
            text=True,
            timeout=GIT_LS_FILES_TIMEOUT_SECONDS,
        )
    except (OSError, subprocess.SubprocessError):
        return False
    return result.returncode == 0


def worktree_matches_index(root: Path, path: str) -> bool:
    try:
        result = subprocess.run(
            ["git", "diff", "--quiet", "--", path],
            cwd=str(root),
            capture_output=True,
            text=True,
            timeout=GIT_DIFF_TIMEOUT_SECONDS,
        )
    except (OSError, subprocess.SubprocessError):
        return False
    return result.returncode == 0


def short_status(root: Path) -> list[str]:
    try:
        result = subprocess.run(
            ["git", "status", "--short"],
            cwd=str(root),
            capture_output=True,
            text=True,
            timeout=GIT_STATUS_TIMEOUT_SECONDS,
        )
    except (OSError, subprocess.SubprocessError):
        return []
    if result.returncode != 0:
        return []
    return [line for line in result.stdout.splitlines() if line.strip()]
