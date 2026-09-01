"""Mirror test for `hydra_engine.work.migration`.

Moves `MigrationPlanTests` and the owner-fallback half of
`OwnerResolutionTests` from `scripts/tests/test_hydra.py`, rewritten against
a hermetic `WorkPaths` fixture with `hydra_engine.ports.git.tracked_files`
mocked directly instead of monkeypatching `hydra.git_tracked_files`.
"""

from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

_SRC = Path(__file__).resolve().parents[3] / "src"
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

from hydra_engine.work import migration  # noqa: E402
from hydra_engine.work.paths import WorkPaths  # noqa: E402


def _paths() -> WorkPaths:
    root = Path(tempfile.mkdtemp(prefix="work-migration-"))
    return WorkPaths(root=root, hydra=root / ".hydra-framework", local=root / ".hydra-framework.local")


def _seed(paths: WorkPaths, rel: str, content: str) -> Path:
    path = paths.hydra / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    return path


def _relative(paths: WorkPaths, plan_key: str, plan: dict) -> list[tuple[str, str]]:
    pairs = []
    for source, destination in plan[plan_key]:
        pairs.append(
            (
                source.relative_to(paths.root).as_posix(),
                destination.relative_to(paths.root).as_posix() if destination else "",
            )
        )
    return pairs


class OwnerForMigratedRecordTests(unittest.TestCase):
    def test_empty_owner_does_not_become_the_slugify_fallback(self) -> None:
        """`slugify("")` returns the literal `task`, which would invent an owner."""
        source = Path("/x/tasks/active")
        self.assertEqual(
            migration.owner_for_migrated_record("Owner:\n", source, Path("x.md"), False, "dana", ""), "dana"
        )
        self.assertEqual(
            migration.owner_for_migrated_record("Owner: unassigned\n", source, Path("x.md"), False, "dana", ""),
            "dana",
        )

    def test_checkpoint_inherits_owner_of_the_task_it_names(self) -> None:
        paths = _paths()
        _seed(paths, "tasks/active/2026-01-01-x.md", "Status: active\nOwner: dana\n")
        checkpoint_source = paths.hydra / "tasks/checkpoints"
        owner = migration.owner_for_migrated_record(
            "Task: .hydra-framework/tasks/active/2026-01-01-x.md\n",
            checkpoint_source,
            Path("2026-01-02-x-checkpoint.md"),
            True,
            "",
            "",
        )
        self.assertEqual(owner, "dana")


class PlanStateMigrationTests(unittest.TestCase):
    def test_records_move_to_their_stated_owner(self) -> None:
        paths = _paths()
        _seed(paths, "tasks/active/2026-01-01-x.md", "Status: active\nOwner: Dana.Reed\n")
        with mock.patch("hydra_engine.ports.git.tracked_files", return_value=[]):
            plan = migration.plan_state_migration(paths, "", "")
        self.assertIn(
            (
                ".hydra-framework/tasks/active/2026-01-01-x.md",
                ".hydra-framework/tasks/personal/dana-reed/2026-01-01-x.md",
            ),
            _relative(paths, "move", plan),
        )

    def test_checkpoints_inherit_the_owner_of_the_task_they_name(self) -> None:
        paths = _paths()
        _seed(paths, "tasks/active/2026-01-01-x.md", "Status: active\nOwner: dana\n")
        _seed(
            paths,
            "tasks/checkpoints/2026-01-02-x-checkpoint.md",
            "Task: .hydra-framework/tasks/active/2026-01-01-x.md\n",
        )
        with mock.patch("hydra_engine.ports.git.tracked_files", return_value=[]):
            plan = migration.plan_state_migration(paths, "", "")
        moves = dict(_relative(paths, "move", plan))
        self.assertEqual(
            moves[".hydra-framework/tasks/checkpoints/2026-01-02-x-checkpoint.md"],
            ".hydra-framework/tasks/personal/dana/checkpoints/2026-01-02-x-checkpoint.md",
        )

    def test_tracked_finished_records_are_deleted(self) -> None:
        paths = _paths()
        _seed(paths, "tasks/completed/2026-01-01-x.md", "Status: completed\n")
        with mock.patch(
            "hydra_engine.ports.git.tracked_files",
            return_value=[".hydra-framework/tasks/completed/2026-01-01-x.md"],
        ):
            plan = migration.plan_state_migration(paths, "", "")
        self.assertEqual(len(plan["delete"]), 1)
        self.assertEqual(plan["retire"], [])

    def test_untracked_finished_records_are_retired_not_deleted(self) -> None:
        """The rule: where Git holds no copy, the working copy is it."""
        paths = _paths()
        _seed(paths, "tasks/archive/2026-01-01-x.md", "Status: completed\n")
        with mock.patch("hydra_engine.ports.git.tracked_files", return_value=[]):
            plan = migration.plan_state_migration(paths, "", "")
        self.assertEqual(plan["delete"], [])
        self.assertEqual(
            _relative(paths, "retire", plan),
            [
                (
                    ".hydra-framework/tasks/archive/2026-01-01-x.md",
                    ".hydra-framework.local/tasks/retired/archive/2026-01-01-x.md",
                )
            ],
        )

    def test_private_stages_move_out_and_their_readmes_are_dropped(self) -> None:
        paths = _paths()
        _seed(paths, "intake/raw/source.md", "x\n")
        _seed(paths, "intake/raw/README.md", "documents the shared directory\n")
        with mock.patch("hydra_engine.ports.git.tracked_files", return_value=[]):
            plan = migration.plan_state_migration(paths, "", "")
        self.assertIn(
            (".hydra-framework/intake/raw/source.md", ".hydra-framework.local/intake/raw/source.md"),
            _relative(paths, "move", plan),
        )
        self.assertEqual(
            [source for source, _ in _relative(paths, "drop", plan)], [".hydra-framework/intake/raw/README.md"]
        )

    def test_nothing_to_migrate_plans_nothing(self) -> None:
        paths = _paths()
        with mock.patch("hydra_engine.ports.git.tracked_files", return_value=[]):
            plan = migration.plan_state_migration(paths, "", "")
        self.assertEqual({key: value for key, value in plan.items() if value}, {})


class MigrationDestinationConflictsTests(unittest.TestCase):
    def test_existing_migration_destination_is_a_conflict(self) -> None:
        paths = _paths()
        source = _seed(paths, "intake/raw/source.md", "new\n")
        destination = paths.local / "intake/raw/source.md"
        destination.parent.mkdir(parents=True)
        destination.write_text("old\n", encoding="utf-8")
        conflicts = migration.migration_destination_conflicts([(source, destination)], paths)
        self.assertEqual(len(conflicts), 1)
        self.assertIn("source.md", conflicts[0])
        self.assertIn("already exists", conflicts[0])

    def test_duplicate_migration_destination_is_a_conflict(self) -> None:
        paths = _paths()
        first = _seed(paths, "intake/raw/first.md", "a\n")
        second = _seed(paths, "intake/raw/second.md", "b\n")
        destination = paths.local / "intake/raw/same.md"
        conflicts = migration.migration_destination_conflicts([(first, destination), (second, destination)], paths)
        self.assertEqual(len(conflicts), 1)
        self.assertIn("both target", conflicts[0])
        self.assertIn("same.md", conflicts[0])


class RemoveEmptyStateDirTests(unittest.TestCase):
    def test_removes_directory_and_gitkeep(self) -> None:
        paths = _paths()
        target = paths.hydra / "tasks/active"
        target.mkdir(parents=True)
        (target / ".gitkeep").write_text("", encoding="utf-8")
        migration.remove_empty_state_dir(target)
        self.assertFalse(target.exists())

    def test_leaves_non_empty_directory_alone(self) -> None:
        paths = _paths()
        target = paths.hydra / "tasks/active"
        target.mkdir(parents=True)
        (target / "x.md").write_text("x\n", encoding="utf-8")
        migration.remove_empty_state_dir(target)
        self.assertTrue(target.exists())


class CleanupAfterApplyTests(unittest.TestCase):
    def test_removes_every_emptied_source_directory(self) -> None:
        paths = _paths()
        for rel in ["intake/raw", "tasks/active", "tasks/completed"]:
            (paths.hydra / rel).mkdir(parents=True)
        migration.cleanup_after_apply(paths)
        for rel in ["intake/raw", "tasks/active", "tasks/completed"]:
            self.assertFalse((paths.hydra / rel).exists())


if __name__ == "__main__":
    unittest.main()
