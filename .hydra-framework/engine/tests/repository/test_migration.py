"""Repository invariant: this repository's own state already matches the
tier layout, so `migrate-state` plans a no-op against it. Moved from
`scripts/tests/test_hydra.py`'s frozen
`MigratedRepositoryTests`, one of the named Hard-Constraint
live-repository classes."""

from __future__ import annotations

import os
import sys
import unittest
from pathlib import Path

_SRC = Path(__file__).resolve().parents[2] / "src"
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

from hydra_engine.ports import git as git_port  # noqa: E402
from hydra_engine.work.migration import plan_state_migration  # noqa: E402
from hydra_engine.work.paths import WorkPaths  # noqa: E402

ROOT = Path(__file__).resolve().parents[4]
PATHS = WorkPaths(root=ROOT, hydra=ROOT / ".hydra-framework", local=ROOT / ".hydra-framework.local")


class MigratedRepositoryTests(unittest.TestCase):
    def test_this_repository_needs_no_migration(self) -> None:
        env_owner = os.environ.get("HYDRA_OWNER", "")
        git_email = git_port.config_email(ROOT)
        plan = plan_state_migration(PATHS, env_owner, git_email)
        self.assertEqual(
            {key: len(value) for key, value in plan.items() if value},
            {},
            "this repository has already migrated; the plan must be a no-op",
        )


if __name__ == "__main__":
    unittest.main()
