"""Mirror test for `hydra_engine.work.placement`.

`TierPlacementNoticeTests` moved from `scripts/tests/test_hydra.py`,
rewritten against the moved logic directly with a temp `WorkPaths` fixture
and explicit owner/email arguments instead of monkeypatching
`hydra.os.environ`.
"""

from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

_SRC = Path(__file__).resolve().parents[3] / "src"
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

from hydra_engine.work import placement  # noqa: E402
from hydra_engine.work.paths import WorkPaths  # noqa: E402


def _paths() -> WorkPaths:
    root = Path(tempfile.mkdtemp(prefix="work-placement-"))
    return WorkPaths(root=root, hydra=root / ".hydra-framework", local=root / ".hydra-framework.local")


class TierPlacementNoticeTests(unittest.TestCase):
    def test_private_content_in_the_shared_tree_is_flagged(self) -> None:
        paths = _paths()
        lines = placement.tier_placement_notice(paths.hydra / "intake/raw/source.md", paths, "me", "")
        self.assertTrue(lines)
        self.assertIn(".hydra-framework.local/intake/raw/", " ".join(lines))

    def test_retired_task_directories_are_flagged(self) -> None:
        paths = _paths()
        for retired in ["active", "checkpoints", "completed", "archive"]:
            lines = placement.tier_placement_notice(paths.hydra / f"tasks/{retired}/2026-01-01-x.md", paths, "me", "")
            self.assertTrue(lines, f"tasks/{retired}/ should be flagged")
            self.assertIn("migrate-state", " ".join(lines))

    def test_correct_placement_is_silent(self) -> None:
        paths = _paths()
        for rel in [".hydra-framework/repo/knowledge/state-tiers.md", ".hydra-framework/intake/promoted/x.md"]:
            self.assertEqual(placement.tier_placement_notice(paths.root / rel, paths, "me", ""), [])
        self.assertEqual(placement.tier_placement_notice(paths.root / "README.md", paths, "me", ""), [])

    def test_outside_root_is_silent(self) -> None:
        paths = _paths()
        self.assertEqual(placement.tier_placement_notice(Path("/etc/hosts"), paths, "me", ""), [])

    def test_editing_another_owners_record_is_flagged(self) -> None:
        paths = _paths()
        lines = placement.tier_placement_notice(
            paths.hydra / "tasks/personal/someone-else/2026-01-01-x.md", paths, "me", ""
        )
        self.assertTrue(lines)
        self.assertIn("handoff", " ".join(lines))

    def test_editing_your_own_record_is_silent(self) -> None:
        paths = _paths()
        self.assertEqual(
            placement.tier_placement_notice(paths.hydra / "tasks/personal/me/2026-01-01-x.md", paths, "me", ""), []
        )

    def test_unresolved_owner_is_silent_rather_than_erroring(self) -> None:
        paths = _paths()
        self.assertEqual(
            placement.tier_placement_notice(
                paths.hydra / "tasks/personal/someone-else/2026-01-01-x.md", paths, "", ""
            ),
            [],
        )


if __name__ == "__main__":
    unittest.main()
