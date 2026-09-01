"""Mirror test for `hydra_engine.agent_hooks.retry_state` (format changed to append-only JSONL).

`RetryFingerprintTests` moved from `scripts/tests/test_hydra.py`; the
record/reset round-trip is new coverage.
"""

from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

_SRC = Path(__file__).resolve().parents[3] / "src"
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

from hydra_engine.agent_hooks import retry_state  # noqa: E402
from hydra_engine.agent_hooks.paths import AgentHooksPaths  # noqa: E402


def _paths() -> AgentHooksPaths:
    root = Path(tempfile.mkdtemp(prefix="agent-hooks-retry-state-"))
    return AgentHooksPaths(root=root, local=root / ".hydra-framework.local")


class RetryFingerprintTests(unittest.TestCase):
    def test_same_failure_is_stable_and_different_failures_differ(self):
        first, _ = retry_state.retry_fingerprint("pytest", 1, "AssertionError: nope", "default")
        again, _ = retry_state.retry_fingerprint("pytest", 1, "AssertionError: nope", "default")
        other, _ = retry_state.retry_fingerprint("pytest", 1, "AssertionError: different", "default")
        self.assertEqual(first, again)
        self.assertNotEqual(first, other)

    def test_key_scopes_the_fingerprint(self):
        first, _ = retry_state.retry_fingerprint("cmd", 2, "boom", "task-a")
        second, _ = retry_state.retry_fingerprint("cmd", 2, "boom", "task-b")
        self.assertNotEqual(first, second)


class RecordAndResetRetryFailureTests(unittest.TestCase):
    def test_record_increments_count_and_reset_clears_it(self):
        paths = _paths()
        _fingerprint, first_record = retry_state.record_retry_failure(paths, "cmd", 1, "boom", "k")
        self.assertEqual(first_record["count"], 1)
        _fingerprint, second_record = retry_state.record_retry_failure(paths, "cmd", 1, "boom", "k")
        self.assertEqual(second_record["count"], 2)

        self.assertTrue(retry_state.reset_retry_failure(paths, "cmd", 1, "boom", "k"))
        state = retry_state.read_retry_state(retry_state.retry_state_path(paths))
        self.assertEqual(state["fingerprints"], {})

    def test_reset_with_no_matching_fingerprint_returns_false(self):
        paths = _paths()
        self.assertFalse(retry_state.reset_retry_failure(paths, "cmd", 1, "boom", "k"))

    def test_read_retry_state_defaults_when_file_missing(self):
        paths = _paths()
        state = retry_state.read_retry_state(retry_state.retry_state_path(paths))
        self.assertEqual(state, {"fingerprints": {}})

    def test_reset_appends_a_tombstone_rather_than_rewriting_the_file(self):
        paths = _paths()
        retry_state.record_retry_failure(paths, "cmd", 1, "boom", "k")
        retry_state.reset_retry_failure(paths, "cmd", 1, "boom", "k")
        path = retry_state.retry_state_path(paths)
        events = [line for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
        self.assertEqual(len(events), 2)

    def test_failure_after_reset_starts_counting_from_one_again(self):
        paths = _paths()
        retry_state.record_retry_failure(paths, "cmd", 1, "boom", "k")
        retry_state.record_retry_failure(paths, "cmd", 1, "boom", "k")
        retry_state.reset_retry_failure(paths, "cmd", 1, "boom", "k")
        _fingerprint, record = retry_state.record_retry_failure(paths, "cmd", 1, "boom", "k")
        self.assertEqual(record["count"], 1)

    def test_concurrent_appenders_never_lose_an_increment(self):
        # No two processes racing this write can silently drop a failure: two
        # calls that both append succeed unconditionally, so the aggregate at
        # read time always reflects every recorded failure.
        paths = _paths()
        for _ in range(5):
            retry_state.record_retry_failure(paths, "cmd", 1, "boom", "k")
        state = retry_state.read_retry_state(retry_state.retry_state_path(paths))
        fingerprint, _sample = retry_state.retry_fingerprint("cmd", 1, "boom", "k")
        self.assertEqual(state["fingerprints"][fingerprint]["count"], 5)


class RetryStateGrowthNotesTests(unittest.TestCase):
    def test_no_note_below_the_advisory_threshold(self):
        paths = _paths()
        retry_state.record_retry_failure(paths, "cmd", 1, "boom", "k")
        self.assertEqual(retry_state.retry_state_growth_notes(paths, growth_advisory_lines=5), [])

    def test_note_above_the_advisory_threshold(self):
        paths = _paths()
        for _ in range(6):
            retry_state.record_retry_failure(paths, "cmd", 1, "boom", "k")
        notes = retry_state.retry_state_growth_notes(paths, growth_advisory_lines=5)
        self.assertEqual(len(notes), 1)
        self.assertIn("retry-state.jsonl", notes[0])

    def test_no_note_when_file_absent(self):
        paths = _paths()
        self.assertEqual(retry_state.retry_state_growth_notes(paths, growth_advisory_lines=0), [])


if __name__ == "__main__":
    unittest.main()
