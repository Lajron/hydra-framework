"""Live-repository smoke test for Hydra engine architecture bounds."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

HYDRA = Path(__file__).resolve().parents[3]
ROOT = HYDRA.parent
SRC = HYDRA / "engine" / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from hydra_engine import architecture  # noqa: E402


class LiveArchitectureBoundsTests(unittest.TestCase):
    def test_live_engine_tree_satisfies_architecture_bounds(self) -> None:
        result = architecture.check(
            package_root=SRC / "hydra_engine",
            test_unit_root=HYDRA / "engine" / "tests" / "unit",
            hydra_shim=HYDRA / "scripts" / "hydra.py",
            repo_root=ROOT,
            composition_root="hydra_engine.cli.dispatch",
        )
        if not result.ok:
            self.fail("\n".join(result.render()))


if __name__ == "__main__":
    unittest.main()
