"""Repository invariants for the personal/private tier boundary.
`TierBoundaryTests` in the old `scripts/tests/test_hydra.py`
mixed genuinely real-repo-dependent assertions with pure/hermetic ones; the
hermetic half (the `PRIVATE_FILE_REF_RE` regex table, the synthetic-tmp-root
owner-mismatch case, and the synthetic-tmp-root shared/private-leftover case)
was already duplicated in `tests/unit/work/{test_tiers,test_task_records}.py`
before this step -- confirmed by reading each site's actual body, not assumed
-- so only the two methods that truly need the live repository move here.
`RetiredTaskDirectoriesTests` (the placement rules' retired directories) lives in
the same file: same tier-boundary concern, same real-repo dependency.
"""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

_SRC = Path(__file__).resolve().parents[2] / "src"
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

from hydra_engine.documents.tokens import read_text  # noqa: E402
from hydra_engine.installation.private_tier import private_tier_ignored  # noqa: E402
from hydra_engine.work.paths import WorkPaths  # noqa: E402
from hydra_engine.work.task_records import iter_personal_task_files, task_header_field  # noqa: E402
from hydra_engine.work.tiers import validate_tier_boundaries  # noqa: E402

ROOT = Path(__file__).resolve().parents[4]
HYDRA = ROOT / ".hydra-framework"
LOCAL = ROOT / ".hydra-framework.local"
PATHS = WorkPaths(root=ROOT, hydra=HYDRA, local=LOCAL)


class RetiredTaskDirectoriesTests(unittest.TestCase):
    def test_retired_task_directories_are_gone(self) -> None:
        """The placement rules removed these. A reappearance means state drifted back."""
        for name in ["active", "checkpoints", "completed", "archive"]:
            self.assertFalse((HYDRA / "tasks" / name).exists(), f"tasks/{name}/ is retired")


class TierBoundaryTests(unittest.TestCase):
    def test_repository_has_no_tier_violations(self) -> None:
        self.assertEqual(validate_tier_boundaries(PATHS), [])

    def test_private_tier_is_effectively_ignored(self) -> None:
        self.assertTrue(private_tier_ignored(ROOT))

    def test_personal_records_carry_owner_and_updated(self) -> None:
        for path in iter_personal_task_files(PATHS):
            text = read_text(path)
            self.assertEqual(
                task_header_field(text, "Owner"),
                path.parent.name,
                "a record's directory is its owner; the header must agree",
            )
            self.assertTrue(task_header_field(text, "Updated"), f"{path} has no Updated: date")


if __name__ == "__main__":
    unittest.main()
