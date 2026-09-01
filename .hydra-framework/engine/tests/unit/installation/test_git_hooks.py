"""Mirror test for `hydra_engine.installation.git_hooks`."""

from __future__ import annotations

import stat
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

_SRC = Path(__file__).resolve().parents[3] / "src"
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

from hydra_engine.installation.git_hooks import (  # noqa: E402
    executable_hook_files,
    hooks_path_matches,
    set_hooks_path,
    unset_hooks_path,
)


def _git_repo() -> Path:
    root = Path(tempfile.mkdtemp(prefix="git-hooks-"))
    subprocess.run(["git", "init", "-q"], cwd=str(root), check=True)
    return root


class ExecutableHookFilesTests(unittest.TestCase):
    def test_makes_hook_files_executable_and_returns_them_sorted(self):
        root = Path(tempfile.mkdtemp(prefix="hooks-dir-"))
        hooks_dir = root / "hooks"
        hooks_dir.mkdir()
        (hooks_dir / "pre-push").write_text("#!/bin/sh\necho hi\n", encoding="utf-8")
        (hooks_dir / "pre-commit").write_text("#!/bin/sh\necho hi\n", encoding="utf-8")
        (hooks_dir / "README.md").write_text("docs\n", encoding="utf-8")

        found = executable_hook_files(hooks_dir)

        self.assertEqual([hook.name for hook in found], ["README.md", "pre-commit", "pre-push"])
        for hook in found:
            self.assertTrue(hooks_dir.joinpath(hook.name).stat().st_mode & stat.S_IXUSR)

    def test_ignores_subdirectories(self):
        root = Path(tempfile.mkdtemp(prefix="hooks-dir-"))
        hooks_dir = root / "hooks"
        hooks_dir.mkdir()
        (hooks_dir / "nested").mkdir()
        found = executable_hook_files(hooks_dir)
        self.assertEqual(found, [])


class HooksPathTests(unittest.TestCase):
    def test_set_hooks_path_writes_git_config(self):
        root = _git_repo()
        ok, error = set_hooks_path(root, ".hydra-framework/hooks")
        self.assertTrue(ok, error)
        result = subprocess.run(
            ["git", "config", "core.hooksPath"], cwd=str(root), capture_output=True, text=True, check=True
        )
        self.assertEqual(result.stdout.strip(), ".hydra-framework/hooks")
        self.assertTrue(hooks_path_matches(root, ".hydra-framework/hooks"))

    def test_hooks_path_matches_rejects_absent_or_different_config(self):
        root = _git_repo()
        self.assertFalse(hooks_path_matches(root, ".hydra-framework/hooks"))
        set_hooks_path(root, "other-hooks")
        self.assertFalse(hooks_path_matches(root, ".hydra-framework/hooks"))

    def test_unset_hooks_path_removes_config(self):
        root = _git_repo()
        set_hooks_path(root, ".hydra-framework/hooks")
        unset_hooks_path(root)
        result = subprocess.run(
            ["git", "config", "core.hooksPath"], cwd=str(root), capture_output=True, text=True
        )
        self.assertNotEqual(result.returncode, 0)

    def test_unset_hooks_path_does_not_raise_when_nothing_to_unset(self):
        root = _git_repo()
        unset_hooks_path(root)  # must not raise even though nothing was set


if __name__ == "__main__":
    unittest.main()
