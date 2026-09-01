"""Repository invariant: every provider-native file in this repository is
Hydra-generated, none unmanaged. Moved
from `scripts/tests/test_hydra.py`'s frozen `SurfaceClassificationTests`, one
of the named Hard-Constraint live-repository classes."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

_SRC = Path(__file__).resolve().parents[2] / "src"
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

from hydra_engine.providers.paths import ProvidersPaths  # noqa: E402
from hydra_engine.providers.reclaim import classify_surfaces, provider_surface_notice  # noqa: E402

ROOT = Path(__file__).resolve().parents[4]
PATHS = ProvidersPaths(root=ROOT, hydra=ROOT / ".hydra-framework")


class SurfaceClassificationTests(unittest.TestCase):
    def test_repository_surfaces_are_all_generated(self) -> None:
        unmanaged = [item for item in classify_surfaces(PATHS) if item["status"] != "generated"]
        self.assertEqual(
            unmanaged, [], "run `hydra.py export-adapters` or `hydra.py reclaim` to resolve unmanaged surfaces"
        )

    def test_non_provider_paths_produce_no_notice(self) -> None:
        self.assertEqual(provider_surface_notice(PATHS, ROOT / "README.md"), [])
        self.assertEqual(provider_surface_notice(PATHS, Path("/etc/hosts")), [])

    def test_ignored_names_produce_no_notice(self) -> None:
        self.assertEqual(provider_surface_notice(PATHS, ROOT / ".claude/skills/README.md"), [])


if __name__ == "__main__":
    unittest.main()
