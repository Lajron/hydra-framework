"""Mirror test for `hydra_engine.installation.paths`."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

_SRC = Path(__file__).resolve().parents[3] / "src"
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

from hydra_engine.installation.paths import InstallationPaths  # noqa: E402


class InstallationPathsTests(unittest.TestCase):
    def test_manifest_path_is_under_hydra(self):
        paths = InstallationPaths(root=Path("/repo"), hydra=Path("/repo/.hydra-framework"))
        self.assertEqual(paths.manifest_path(), Path("/repo/.hydra-framework/manifest.yaml"))

    def test_hooks_dir_is_under_hydra(self):
        paths = InstallationPaths(root=Path("/repo"), hydra=Path("/repo/.hydra-framework"))
        self.assertEqual(paths.hooks_dir(), Path("/repo/.hydra-framework/hooks"))


if __name__ == "__main__":
    unittest.main()
