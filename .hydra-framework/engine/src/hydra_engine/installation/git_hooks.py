"""Point Git at the tracked hooks directory.

Writing `core.hooksPath` is a real Git-config mutation, not a determinism
concern -- it shells out to real `git` independent of `hydra_engine.ports.git`,
which exists to mediate *determinism*, not every git invocation.
"""

from __future__ import annotations

import subprocess
from pathlib import Path


def executable_hook_files(hooks_dir: Path) -> list[Path]:
    """Sorted hook files in `hooks_dir`, made executable as a side effect."""
    files = [hook for hook in sorted(hooks_dir.iterdir()) if hook.is_file()]
    for hook in files:
        hook.chmod(hook.stat().st_mode | 0o111)
    return files


def unset_hooks_path(root: Path) -> None:
    subprocess.run(["git", "config", "--unset", "core.hooksPath"], cwd=str(root), check=False)


def set_hooks_path(root: Path, relative: str) -> tuple[bool, str]:
    result = subprocess.run(
        ["git", "config", "core.hooksPath", relative], cwd=str(root), capture_output=True, text=True
    )
    return result.returncode == 0, result.stderr.strip()


def hooks_path_matches(root: Path, relative: str) -> bool:
    result = subprocess.run(
        ["git", "config", "--get", "core.hooksPath"], cwd=str(root), capture_output=True, text=True
    )
    return result.returncode == 0 and result.stdout.strip() == relative
