"""Mirror test for `hydra_engine.intake.paths`."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

_SRC = Path(__file__).resolve().parents[3] / "src"
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

from hydra_engine.intake import paths  # noqa: E402


class IntakePathsTests(unittest.TestCase):
    def test_staging_root_is_dot_migrations_under_repo_root(self):
        bundle = paths.IntakePaths(root=Path("/tmp/repo"), hydra=Path("/tmp/repo/.hydra-framework"))
        self.assertEqual(bundle.staging_root(), Path("/tmp/repo/.migrations"))

    def test_workspace_root_is_intake_migrations_under_hydra(self):
        bundle = paths.IntakePaths(root=Path("/tmp/repo"), hydra=Path("/tmp/repo/.hydra-framework"))
        self.assertEqual(bundle.workspace_root(), Path("/tmp/repo/.hydra-framework/intake/migrations"))


if __name__ == "__main__":
    unittest.main()
