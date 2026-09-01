"""Mirror test for `hydra_engine.agent_hooks.io`."""

from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

_SRC = Path(__file__).resolve().parents[3] / "src"
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

from hydra_engine.agent_hooks import io  # noqa: E402
from hydra_engine.agent_hooks.paths import AgentHooksPaths  # noqa: E402


class ReadStdinOrFileTests(unittest.TestCase):
    def test_reads_from_file_when_path_given(self):
        path = Path(tempfile.mkdtemp(prefix="agent-hooks-io-")) / "log.txt"
        path.write_text("hello\n", encoding="utf-8")
        self.assertEqual(io.read_stdin_or_file(str(path)), "hello\n")


class StorePrivateLogTests(unittest.TestCase):
    def test_writes_under_local_logs_named_by_hint(self):
        root = Path(tempfile.mkdtemp(prefix="agent-hooks-io-"))
        paths = AgentHooksPaths(root=root, local=root / ".hydra-framework.local")
        target = io.store_private_log(paths, "payload\n", "My Command")
        self.assertTrue(target.is_relative_to(paths.local / "logs"))
        self.assertIn("my-command", target.name)
        self.assertEqual(target.read_text(encoding="utf-8"), "payload\n")


if __name__ == "__main__":
    unittest.main()
