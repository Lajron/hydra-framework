"""Mirror tests for `hydra_engine.command_output.rendering`."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

_SRC = Path(__file__).resolve().parents[3] / "src"
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

from hydra_engine.command_output import rendering  # noqa: E402
from hydra_engine.command_output.model import CommandOutput  # noqa: E402


class RenderingTests(unittest.TestCase):
    def test_redacts_obvious_secret_literals(self):
        text = rendering.redact_obvious_secrets("TOKEN=\"abc secret\" curl --api-key 'secret two' -H \"Authorization: Bearer aaa\" https://x/?token=\"one two\"")
        self.assertNotIn("abc", text)
        self.assertNotIn("secret", text)
        self.assertNotIn("Bearer", text)
        self.assertNotIn("one", text)

    def test_reduction_keeps_error_context_and_omits_restore_noise(self):
        output = "Determining projects to restore...\nA.cs(5,1): error CS1001: bad\nBuild FAILED.\n"
        reduction = rendering.reduce_with_family(CommandOutput("manual", "", "dotnet build", ".", 1, output), "dotnet-build", "dotnet-build", 20)
        rendered = rendering.render_reduction(reduction)
        self.assertIn("CS1001", rendered)
        self.assertNotIn("Determining projects", rendered)

    def test_unknown_reduction_omits_raw_output(self):
        reduction = rendering.unknown_reduction(CommandOutput("manual", "", "custom", ".", 0, "secret-ish raw text"))
        self.assertFalse(reduction.has_reducer)
        self.assertIn("raw output omitted", rendering.render_reduction(reduction))

    def test_known_reducer_without_signal_does_not_emit_raw_fallback(self):
        reduction = rendering.reduce_with_family(CommandOutput("manual", "", "docker logs", ".", 0, "tenant body\nsigned token"), "docker-logs", "docker-logs", 20)
        rendered = rendering.render_reduction(reduction)
        self.assertNotIn("tenant body", rendered)
        self.assertNotIn("signed token", rendered)
        self.assertIn("<no signal lines selected>", rendered)


if __name__ == "__main__":
    unittest.main()
