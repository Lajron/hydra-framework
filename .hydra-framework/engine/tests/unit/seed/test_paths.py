"""Mirror test for `hydra_engine.seed.paths`."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

_SRC = Path(__file__).resolve().parents[3] / "src"
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

from hydra_engine.seed.paths import SeedPaths  # noqa: E402


class SeedPathsTests(unittest.TestCase):
    def test_fields_round_trip(self):
        root = Path("/tmp/example")
        hydra = root / ".hydra-framework"
        ledger = hydra / "evolution/adaptations.md"
        paths = SeedPaths(root=root, hydra=hydra, adaptation_ledger=ledger)
        self.assertEqual(paths.root, root)
        self.assertEqual(paths.hydra, hydra)
        self.assertEqual(paths.adaptation_ledger, ledger)


if __name__ == "__main__":
    unittest.main()
