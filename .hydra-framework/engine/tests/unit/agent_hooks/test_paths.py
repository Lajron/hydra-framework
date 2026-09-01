"""Mirror test for `hydra_engine.agent_hooks.paths`."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

_SRC = Path(__file__).resolve().parents[3] / "src"
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

from hydra_engine.agent_hooks import paths  # noqa: E402


class AgentHooksPathsTests(unittest.TestCase):
    def test_holds_root_and_local_verbatim(self):
        root = Path("/tmp/repo")
        local = Path("/tmp/repo/.hydra-framework.local")
        bundle = paths.AgentHooksPaths(root=root, local=local)
        self.assertEqual(bundle.root, root)
        self.assertEqual(bundle.local, local)


if __name__ == "__main__":
    unittest.main()
