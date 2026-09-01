"""Smoke tests for the contract harness."""

from __future__ import annotations

import unittest

from .goldens.fixtures import ordered_manifest
from .harness import run_command


class HarnessTests(unittest.TestCase):
    def test_run_command_reports_exit_code_and_stdout(self):
        outcome = run_command(["board"])
        self.assertEqual(outcome.exit_code, 0)
        self.assertIn("no active task records", outcome.stdout)

    def test_run_command_isolates_fixture_root(self):
        fixture = {
            ".hydra-framework/tasks/personal/alice/2026-08-17-example.md": (
                "---\nname: example\nowner: alice\nstatus: active\n---\n\nbody\n"
            ),
        }
        outcome = run_command(["board"], fixture=fixture)
        self.assertEqual(outcome.exit_code, 0)

    def test_manifest_reflects_files_written(self):
        fixture = {"note.txt": "hello\n"}
        outcome = run_command(["board"], fixture=fixture)
        self.assertIn("note.txt", outcome.manifest)
        self.assertIsNotNone(outcome.manifest["note.txt"])

    def test_ordered_manifest_sorts_without_previous_golden(self):
        manifest = {"b.md": "b", "a.md": "a"}
        self.assertEqual(list(ordered_manifest(manifest)), ["a.md", "b.md"])

    def test_ordered_manifest_preserves_previous_golden_order(self):
        manifest = {"a.md": "new-a", "b.md": "new-b", "c.md": "new-c"}
        previous = {"b.md": "old-b", "a.md": "old-a"}
        ordered = ordered_manifest(manifest, previous)
        self.assertEqual(list(ordered), ["b.md", "a.md", "c.md"])
        self.assertEqual(ordered["a.md"], "new-a")

    def test_shim_module_constant_is_never_mutated_by_a_fixture_call(self):
        # `hydra.py`'s global-swap-and-restore
        # mechanism is gone: every command now takes root state through
        # `ctx`, so a fixture-scoped call has nothing module-level to mutate
        # or restore in the first place.
        import hydra

        before = hydra._HYDRA
        run_command(["board"])
        self.assertEqual(hydra._HYDRA, before)

    def test_pre_run_hook_runs_after_fixture_before_command(self):
        seen: list[bool] = []

        def pre_run(root):
            seen.append((root / "note.txt").exists())

        run_command(["board"], fixture={"note.txt": "hello\n"}, pre_run=pre_run)
        self.assertEqual(seen, [True])


if __name__ == "__main__":
    unittest.main()
