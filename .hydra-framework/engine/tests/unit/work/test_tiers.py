"""Mirror test for `hydra_engine.work.tiers`."""

from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

_SRC = Path(__file__).resolve().parents[3] / "src"
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

from hydra_engine.work import tiers  # noqa: E402
from hydra_engine.work.paths import WorkPaths  # noqa: E402


def _paths() -> WorkPaths:
    root = Path(tempfile.mkdtemp(prefix="work-tiers-"))
    return WorkPaths(root=root, hydra=root / ".hydra-framework", local=root / ".hydra-framework.local")


class PrivateFileRefReTests(unittest.TestCase):
    def test_private_content_citations_are_rejected(self) -> None:
        for bad in [
            "See .hydra-framework.local/intake/raw/2026-07-29-source.md for detail.",
            "`.hydra-framework.local/notes/2026-07-30.md`",
            "(.hydra-framework.local/tasks/retired/archive/old.md)",
        ]:
            self.assertTrue(tiers.PRIVATE_FILE_REF_RE.search(bad), f"should be rejected: {bad}")

    def test_conventions_placeholders_and_directories_are_allowed(self) -> None:
        for good in [
            ".hydra-framework.local/intake/raw/<date>-<slug>-source.md",
            "Keep private state in `.hydra-framework.local/`.",
            "Use the private monitoring area for local hook policy.",
        ]:
            self.assertIsNone(tiers.PRIVATE_FILE_REF_RE.search(good), f"should be allowed: {good}")


class ValidateTierBoundariesTests(unittest.TestCase):
    def test_private_tier_content_in_shared_tree_is_reported(self) -> None:
        paths = _paths()
        misplaced = paths.hydra / "intake/raw/source.md"
        misplaced.parent.mkdir(parents=True)
        misplaced.write_text("x\n", encoding="utf-8")
        with mock.patch("hydra_engine.ports.git.tracked_files", return_value=[]):
            errors = tiers.validate_tier_boundaries(paths)
        self.assertEqual(len(errors), 1)
        self.assertIn(".hydra-framework/intake/raw", errors[0])

    def test_clean_tree_reports_nothing(self) -> None:
        paths = _paths()
        paths.hydra.mkdir(parents=True)
        with mock.patch("hydra_engine.ports.git.tracked_files", return_value=[]):
            errors = tiers.validate_tier_boundaries(paths)
        self.assertEqual(errors, [])

    def test_task_readiness_may_name_required_private_file(self) -> None:
        paths = _paths()
        task = paths.owner_task_dir("dana") / "2026-01-01-x.md"
        task.parent.mkdir(parents=True)
        task.write_text(
            "## Readiness\n\n"
            "- Required dependencies, services, generated artifacts, or private local requirements: "
            ".hydra-framework.local/notes/resume.md\n",
            encoding="utf-8",
        )
        with mock.patch("hydra_engine.ports.git.tracked_files", return_value=[]):
            errors = tiers.validate_tier_boundaries(paths)
        self.assertEqual(errors, [])

    def test_private_file_reference_outside_resumability_fields_is_reported(self) -> None:
        paths = _paths()
        task = paths.owner_task_dir("dana") / "2026-01-01-x.md"
        task.parent.mkdir(parents=True)
        task.write_text(
            "## Validation\n\n"
            "- See .hydra-framework.local/notes/evidence.md for proof.\n",
            encoding="utf-8",
        )
        with mock.patch("hydra_engine.ports.git.tracked_files", return_value=[]):
            errors = tiers.validate_tier_boundaries(paths)
        self.assertEqual(len(errors), 1)
        self.assertIn("cites private file", errors[0])

    def test_retired_task_directory_with_records_is_reported(self) -> None:
        paths = _paths()
        active = paths.hydra / "tasks/active/2026-01-01-x.md"
        active.parent.mkdir(parents=True)
        active.write_text("x\n", encoding="utf-8")
        with mock.patch("hydra_engine.ports.git.tracked_files", return_value=[]):
            errors = tiers.validate_tier_boundaries(paths)
        self.assertTrue(any("superseded task directory" in error for error in errors))

    def test_tracked_private_file_is_reported(self) -> None:
        paths = _paths()
        paths.hydra.mkdir(parents=True)
        with mock.patch(
            "hydra_engine.ports.git.tracked_files",
            return_value=[".hydra-framework.local/notes/2026-01-01.md"],
        ):
            errors = tiers.validate_tier_boundaries(paths)
        self.assertEqual(len(errors), 1)
        self.assertIn("private-tier file is tracked in Git", errors[0])

    def test_tracked_example_tree_is_no_longer_exempt(self) -> None:
        paths = _paths()
        paths.hydra.mkdir(parents=True)
        example = ".hydra-framework" ".local" ".example/README.md"
        with mock.patch("hydra_engine.ports.git.tracked_files", return_value=[example]):
            errors = tiers.validate_tier_boundaries(paths)
        self.assertEqual(len(errors), 1)
        self.assertIn("private-tier file is tracked in Git", errors[0])


if __name__ == "__main__":
    unittest.main()
