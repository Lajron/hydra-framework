"""Mirror test for `hydra_engine.work.paths`."""

from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

_SRC = Path(__file__).resolve().parents[3] / "src"
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

from hydra_engine.work.paths import WorkPaths  # noqa: E402


def _paths() -> WorkPaths:
    root = Path(tempfile.mkdtemp(prefix="work-paths-"))
    return WorkPaths(root=root, hydra=root / ".hydra-framework", local=root / ".hydra-framework.local")


class WorkPathsTests(unittest.TestCase):
    def test_personal_tasks_root_is_under_hydra(self) -> None:
        paths = _paths()
        self.assertEqual(paths.personal_tasks_root(), paths.hydra / "tasks/personal")

    def test_owner_task_dir_is_under_personal_tasks_root(self) -> None:
        paths = _paths()
        self.assertEqual(paths.owner_task_dir("dana"), paths.hydra / "tasks/personal/dana")

    def test_local_notes_dir_is_under_local(self) -> None:
        paths = _paths()
        self.assertEqual(paths.local_notes_dir(), paths.local / "notes")

    def test_retired_tasks_root_is_under_local(self) -> None:
        paths = _paths()
        self.assertEqual(paths.retired_tasks_root(), paths.local / "tasks/retired")


if __name__ == "__main__":
    unittest.main()
