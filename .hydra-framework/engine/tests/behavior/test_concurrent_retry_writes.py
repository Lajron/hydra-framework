"""A2 concurrency probe:
the old read-the-whole-file-increment-write-it-back retry counter silently
lost an increment whenever two hook processes raced -- the normal case once
an agent spawns subagents, and the exact safety brake `AGENTS.md` relies on
to halt a looping agent. Fork real OS processes racing the same fingerprint
and assert the aggregate count is exact, not just "close"."""

from __future__ import annotations

import multiprocessing
import sys
import tempfile
import unittest
from pathlib import Path

_SRC = Path(__file__).resolve().parents[2] / "src"
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

from hydra_engine.agent_hooks.paths import AgentHooksPaths  # noqa: E402
from hydra_engine.agent_hooks.retry_state import (  # noqa: E402
    read_retry_state,
    record_retry_failure,
    retry_fingerprint,
    retry_state_path,
)

_PROCESSES = 8
_EVENTS_PER_PROCESS = 25
_COMMAND, _EXIT_CODE, _TEXT, _KEY = "flaky-command", 1, "boom", "shared-key"


def _append_batch(root: Path, local: Path, count: int) -> None:
    paths = AgentHooksPaths(root=root, local=local)
    for _ in range(count):
        record_retry_failure(paths, _COMMAND, _EXIT_CODE, _TEXT, _KEY)


class ConcurrentRetryWriteTests(unittest.TestCase):
    def test_forked_processes_racing_the_same_fingerprint_lose_no_events(self):
        root = Path(tempfile.mkdtemp(prefix="concurrent-retry-"))
        local = root / ".hydra-framework.local"
        processes = [
            multiprocessing.Process(target=_append_batch, args=(root, local, _EVENTS_PER_PROCESS))
            for _ in range(_PROCESSES)
        ]
        for process in processes:
            process.start()
        for process in processes:
            process.join()
        for process in processes:
            self.assertEqual(process.exitcode, 0)

        fingerprint, _sample = retry_fingerprint(_COMMAND, _EXIT_CODE, _TEXT, _KEY)
        paths = AgentHooksPaths(root=root, local=local)
        state = read_retry_state(retry_state_path(paths))
        self.assertEqual(state["fingerprints"][fingerprint]["count"], _PROCESSES * _EVENTS_PER_PROCESS)


if __name__ == "__main__":
    unittest.main()
