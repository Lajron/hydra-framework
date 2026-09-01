"""Mirror tests for `hydra_engine.command_output.telemetry`."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

_SRC = Path(__file__).resolve().parents[3] / "src"
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

from hydra_engine.command_output import telemetry  # noqa: E402
from hydra_engine.command_output.model import Reduction  # noqa: E402


class CommandOutputTelemetryTests(unittest.TestCase):
    def test_structural_payload_omits_raw_command_output(self):
        reduction = Reduction("s", "manual", "Bash", "dotnet build", ".", 1, "dotnet-build", "dotnet-build", "1", "summary", (), 4, 20, 5, 100, session_id="s1")
        payload = telemetry.structural_payload(reduction)
        self.assertNotIn("command_output", payload)
        self.assertNotIn("tool_name", payload)
        self.assertEqual(payload["event_kind"], "command_output.reducer_outcome")
        self.assertEqual(payload["command_head"], "dotnet")

    def test_redaction_gate_keeps_structural_fields_and_hashes_session(self):
        reduction = Reduction("s", "manual", "Bash", "dotnet build", ".", 1, "dotnet-build", "dotnet-build", "1", "summary", (), 4, 20, 5, 100, session_id="s1")
        result = telemetry.redact_reducer_event(reduction, salt="salt")
        self.assertEqual(result.shared["command_family"], "dotnet-build")
        self.assertIn("session_id_hash", result.shared)
        self.assertNotIn("session_id", result.shared)


if __name__ == "__main__":
    unittest.main()
