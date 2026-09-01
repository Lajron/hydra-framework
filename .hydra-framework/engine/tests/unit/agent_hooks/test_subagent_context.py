"""Mirror test for `hydra_engine.agent_hooks.subagent_context`."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

_SRC = Path(__file__).resolve().parents[3] / "src"
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

from hydra_engine.agent_hooks import subagent_context  # noqa: E402
from hydra_engine.knowledge.candidates import approx_tokens  # noqa: E402


class SubagentContextTests(unittest.TestCase):
    def test_context_points_to_bounded_read_only_commands(self):
        text = subagent_context.build_subagent_context(["hydra-framework"])
        self.assertIn("knowledge-search", text)
        self.assertIn("delegation-brief", text)
        self.assertIn("board", text)
        self.assertIn("Stop rules:", text)
        self.assertNotIn("spend", text.lower())

    def test_context_names_only_a_bounded_package_prefix(self):
        text = subagent_context.build_subagent_context([f"package-{index}" for index in range(20)])
        self.assertIn("and 14 more", text)
        self.assertNotIn("package-19", text)

    def test_context_stays_within_hook_budget(self):
        text = subagent_context.build_subagent_context([f"package-{index}" for index in range(50)])
        self.assertLessEqual(approx_tokens(text), subagent_context.SUBAGENT_CONTEXT_TOKEN_BUDGET)

    def test_context_is_worded_as_pointers_not_instructions_to_override(self):
        text = subagent_context.build_subagent_context(["hydra-framework"]).lower()
        for phrase in ("you must", "ignore", "system-reminder"):
            self.assertNotIn(phrase, text)


if __name__ == "__main__":
    unittest.main()
