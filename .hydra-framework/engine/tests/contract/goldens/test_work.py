"""work goldens: task start/checkpoint/handoff/complete, board,
note, migrate-state."""

from __future__ import annotations

import unittest
from unittest import mock

from .fixtures import TASK_TEMPLATE, assert_golden, run_golden

OWNER = "fixture-owner"
TASK_PATH = ".hydra-framework/tasks/personal/fixture-owner/2026-01-01-fixture-task.md"
TASK_CONTENT = (
    TASK_TEMPLATE.replace("<short-name>", "fixture-task")
    .replace("Owner: unassigned", f"Owner: {OWNER}")
    .replace("Created: YYYY-MM-DD", "Created: 2026-01-01")
    .replace("Updated: YYYY-MM-DD", "Updated: 2026-01-01")
)


class WorkGoldenTests(unittest.TestCase):
    def test_task_start_happy_path(self):
        with mock.patch("hydra_engine.ports.git.stage_file", return_value=True):
            outcome = run_golden(["task", "start", "fixture-task", "--goal", "Do the fixture thing."], owner=OWNER)
        assert_golden(self, "work-task-start", outcome)

    def test_task_checkpoint_happy_path(self):
        with mock.patch("hydra_engine.ports.git.stage_file", return_value=True):
            outcome = run_golden(["task", "checkpoint", TASK_PATH], extra_fixture={TASK_PATH: TASK_CONTENT}, owner=OWNER)
        assert_golden(self, "work-task-checkpoint", outcome)

    def test_task_handoff_happy_path(self):
        outcome = run_golden(
            ["task", "handoff", TASK_PATH, "--to", "other-owner"],
            extra_fixture={TASK_PATH: TASK_CONTENT},
            owner=OWNER,
        )
        assert_golden(self, "work-task-handoff", outcome)

    def test_task_complete_happy_path(self):
        with (
            mock.patch("hydra_engine.ports.git.is_tracked", return_value=True),
            mock.patch("hydra_engine.ports.git.worktree_matches_index", return_value=True),
            mock.patch("hydra_engine.ports.git.stage_file", return_value=True),
            mock.patch(
                "hydra_engine.ports.git.short_status",
                return_value=["D  .hydra-framework/tasks/personal/fixture-owner/2026-01-01-fixture-task.md"],
            ),
        ):
            outcome = run_golden(
                ["task", "complete", TASK_PATH, "--outcome", "none"],
                extra_fixture={TASK_PATH: TASK_CONTENT},
                owner=OWNER,
            )
        assert_golden(self, "work-task-complete", outcome)

    def test_board_happy_path(self):
        """No task records: still a real happy path (`no active task
        records`). A populated board is covered below."""
        outcome = run_golden(["board"])
        assert_golden(self, "work-board", outcome)

    def test_note_happy_path(self):
        outcome = run_golden(["note", "hello", "world"])
        assert_golden(self, "work-note", outcome)

    def test_migrate_state_happy_path(self):
        """Nothing to migrate: still a real happy path (`nothing
        to migrate`). An actual migration is covered below."""
        outcome = run_golden(["migrate-state"])
        assert_golden(self, "work-migrate-state", outcome)

    def test_task_start_already_exists_refusal(self):
        outcome = run_golden(
            ["task", "start", "fixture-task", "--goal", "Do the fixture thing."],
            extra_fixture={TASK_PATH: TASK_CONTENT},
            owner=OWNER,
        )
        assert_golden(self, "work-task-start-already-exists", outcome)

    def test_task_checkpoint_already_exists_refusal(self):
        checkpoint_path = (
            ".hydra-framework/tasks/personal/fixture-owner/checkpoints/2026-01-01-fixture-task-checkpoint.md"
        )
        outcome = run_golden(
            ["task", "checkpoint", TASK_PATH],
            extra_fixture={TASK_PATH: TASK_CONTENT, checkpoint_path: "# Checkpoint: fixture-task\n"},
            owner=OWNER,
        )
        assert_golden(self, "work-task-checkpoint-already-exists", outcome)

    def test_task_checkpoint_owner_mismatch_refusal(self):
        outcome = run_golden(
            ["task", "checkpoint", TASK_PATH],
            extra_fixture={TASK_PATH: TASK_CONTENT},
            owner="other-owner",
        )
        assert_golden(self, "work-task-checkpoint-owner-mismatch", outcome)

    def test_task_checkpoint_owner_mismatch_force(self):
        with mock.patch("hydra_engine.ports.git.stage_file", return_value=True):
            outcome = run_golden(
                ["task", "checkpoint", TASK_PATH, "--force"],
                extra_fixture={TASK_PATH: TASK_CONTENT},
                owner="other-owner",
            )
        assert_golden(self, "work-task-checkpoint-owner-mismatch-force", outcome)

    # A `task checkpoint`/`handoff`/`complete` "Task not found" refusal prints
    # the raw absolute path it was given, which embeds the harness's own
    # per-run tmpdir -- not scrubbable with the existing external_file()/
    # external_dir() placeholders, which cover a *second* named root, not the
    # fixture root itself. Covered instead by
    # `commands/test_work.py::CommandTaskCheckpointTests.test_missing_task_is_a_refusal`
    # (and its handoff/complete siblings), which assert the message
    # substring directly against a real temp path with no golden to embed it in.

    def test_task_handoff_already_exists_refusal(self):
        destination = ".hydra-framework/tasks/personal/other-owner/2026-01-01-fixture-task.md"
        outcome = run_golden(
            ["task", "handoff", TASK_PATH, "--to", "other-owner"],
            extra_fixture={TASK_PATH: TASK_CONTENT, destination: TASK_CONTENT},
            owner=OWNER,
        )
        assert_golden(self, "work-task-handoff-already-exists", outcome)

    def test_task_handoff_owner_mismatch_refusal(self):
        outcome = run_golden(
            ["task", "handoff", TASK_PATH, "--to", "new-owner"],
            extra_fixture={TASK_PATH: TASK_CONTENT},
            owner="other-owner",
        )
        assert_golden(self, "work-task-handoff-owner-mismatch", outcome)

    def test_task_handoff_owner_mismatch_force(self):
        outcome = run_golden(
            ["task", "handoff", TASK_PATH, "--to", "new-owner", "--force"],
            extra_fixture={TASK_PATH: TASK_CONTENT},
            owner="other-owner",
        )
        assert_golden(self, "work-task-handoff-owner-mismatch-force", outcome)

    def test_task_handoff_force_destination_collision_refusal(self):
        destination = ".hydra-framework/tasks/personal/other-owner/2026-01-01-fixture-task.md"
        outcome = run_golden(
            ["task", "handoff", TASK_PATH, "--to", "other-owner", "--force"],
            extra_fixture={TASK_PATH: TASK_CONTENT, destination: TASK_CONTENT},
            owner=OWNER,
        )
        assert_golden(self, "work-task-handoff-force-destination-collision", outcome)

    def test_task_complete_outcome_missing_refusal(self):
        outcome = run_golden(
            ["task", "complete", TASK_PATH, "--outcome", "repo/knowledge/no-such-file.md"],
            extra_fixture={TASK_PATH: TASK_CONTENT},
            owner=OWNER,
        )
        assert_golden(self, "work-task-complete-outcome-missing", outcome)

    def test_task_complete_private_outcome_refusal(self):
        outcome = run_golden(
            ["task", "complete", TASK_PATH, "--outcome", ".hydra-framework.local/notes/outcome.md"],
            extra_fixture={
                TASK_PATH: TASK_CONTENT,
                ".hydra-framework.local/notes/outcome.md": "private\n",
            },
            owner=OWNER,
        )
        assert_golden(self, "work-task-complete-private-outcome", outcome)

    def test_task_complete_owner_mismatch_refusal(self):
        outcome = run_golden(
            ["task", "complete", TASK_PATH, "--outcome", "none"],
            extra_fixture={TASK_PATH: TASK_CONTENT},
            owner="other-owner",
        )
        assert_golden(self, "work-task-complete-owner-mismatch", outcome)

    def test_task_complete_owner_mismatch_force(self):
        with (
            mock.patch("hydra_engine.ports.git.is_tracked", return_value=True),
            mock.patch("hydra_engine.ports.git.worktree_matches_index", return_value=True),
            mock.patch("hydra_engine.ports.git.stage_file", return_value=True),
            mock.patch(
                "hydra_engine.ports.git.short_status",
                return_value=["D  .hydra-framework/tasks/personal/fixture-owner/2026-01-01-fixture-task.md"],
            ),
        ):
            outcome = run_golden(
                ["task", "complete", TASK_PATH, "--outcome", "none", "--force"],
                extra_fixture={TASK_PATH: TASK_CONTENT},
                owner="other-owner",
            )
        assert_golden(self, "work-task-complete-owner-mismatch-force", outcome)

    def test_task_complete_untracked_record_refusal(self):
        with mock.patch("hydra_engine.ports.git.is_tracked", return_value=False):
            outcome = run_golden(
                ["task", "complete", TASK_PATH, "--outcome", "none"],
                extra_fixture={TASK_PATH: TASK_CONTENT},
                owner=OWNER,
            )
        assert_golden(self, "work-task-complete-untracked", outcome)

    def test_task_complete_untracked_checkpoint_refusal(self):
        checkpoint_path = (
            ".hydra-framework/tasks/personal/fixture-owner/checkpoints/2026-01-01-fixture-task-checkpoint.md"
        )

        def tracked_except_checkpoint(_root, path):
            return path != checkpoint_path

        with (
            mock.patch("hydra_engine.ports.git.is_tracked", side_effect=tracked_except_checkpoint),
            mock.patch("hydra_engine.ports.git.worktree_matches_index", return_value=True),
        ):
            outcome = run_golden(
                ["task", "complete", TASK_PATH, "--outcome", "none"],
                extra_fixture={TASK_PATH: TASK_CONTENT, checkpoint_path: "# Checkpoint: fixture-task\n"},
                owner=OWNER,
            )
        assert_golden(self, "work-task-complete-untracked-checkpoint", outcome)

    def test_board_populated(self):
        other_task_path = ".hydra-framework/tasks/personal/other-owner/2026-01-01-other-task.md"
        other_task_content = (
            TASK_TEMPLATE.replace("<short-name>", "other-task")
            .replace("Owner: unassigned", "Owner: other-owner")
            .replace("Created: YYYY-MM-DD", "Created: 2026-01-01")
            .replace("Updated: YYYY-MM-DD", "Updated: 2026-01-01")
        )
        checkpoint_path = ".hydra-framework/tasks/personal/fixture-owner/checkpoints/2026-01-01-fixture-task-checkpoint.md"
        outcome = run_golden(
            ["board"],
            extra_fixture={
                TASK_PATH: TASK_CONTENT,
                other_task_path: other_task_content,
                checkpoint_path: "# Checkpoint: fixture-task\n",
            },
        )
        assert_golden(self, "work-board-populated", outcome)

    def test_note_empty_text_refusal(self):
        outcome = run_golden(["note"], stdin="")
        assert_golden(self, "work-note-empty-refusal", outcome)

    def test_migrate_state_dry_run_with_plan(self):
        legacy_path = ".hydra-framework/tasks/active/2026-01-01-legacy-task.md"
        legacy_content = (
            TASK_TEMPLATE.replace("<short-name>", "legacy-task")
            .replace("Owner: unassigned", f"Owner: {OWNER}")
            .replace("Created: YYYY-MM-DD", "Created: 2026-01-01")
            .replace("Updated: YYYY-MM-DD", "Updated: 2026-01-01")
        )
        outcome = run_golden(["migrate-state"], extra_fixture={legacy_path: legacy_content})
        assert_golden(self, "work-migrate-state-dry-run-with-plan", outcome)

    def test_migrate_state_apply(self):
        legacy_path = ".hydra-framework/tasks/active/2026-01-01-legacy-task.md"
        legacy_content = (
            TASK_TEMPLATE.replace("<short-name>", "legacy-task")
            .replace("Owner: unassigned", f"Owner: {OWNER}")
            .replace("Created: YYYY-MM-DD", "Created: 2026-01-01")
            .replace("Updated: YYYY-MM-DD", "Updated: 2026-01-01")
        )
        outcome = run_golden(["migrate-state", "--apply"], extra_fixture={legacy_path: legacy_content})
        assert_golden(self, "work-migrate-state-apply", outcome)


if __name__ == "__main__":
    unittest.main()
