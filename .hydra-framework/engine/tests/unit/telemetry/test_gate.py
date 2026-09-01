"""Mirror tests for `hydra_engine.telemetry.gate`."""

from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

_SRC = Path(__file__).resolve().parents[3] / "src"
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

from hydra_engine.telemetry import gate, writer  # noqa: E402


class TelemetryGateTests(unittest.TestCase):
    def test_gate_passes_synthetic_and_local_typed_events(self):
        root = Path(tempfile.mkdtemp(prefix="telemetry-gate-"))
        hydra = root / ".hydra-framework"
        redaction_path = hydra / "engine/src/hydra_engine/telemetry/redaction.py"
        redaction_path.parent.mkdir(parents=True)
        redaction_path.write_text("fixture\n", encoding="utf-8")
        local = root / ".hydra-framework.local"
        writer.record_knowledge_route(local, True)
        attestation = gate.run_gate(local=local, hydra=hydra)
        self.assertEqual(attestation.verdict, "pass")
        self.assertGreaterEqual(attestation.event_count, 4)
        self.assertIn("knowledge.route", attestation.distinct_event_kinds)
        self.assertIn("event_kind", attestation.distinct_field_names)

    def test_unclassified_local_field_fails_gate(self):
        root = Path(tempfile.mkdtemp(prefix="telemetry-gate-fail-"))
        hydra = root / ".hydra-framework"
        redaction_path = hydra / "engine/src/hydra_engine/telemetry/redaction.py"
        redaction_path.parent.mkdir(parents=True)
        redaction_path.write_text("fixture\n", encoding="utf-8")
        local = root / ".hydra-framework.local"
        path = writer.events_path(local)
        path.parent.mkdir(parents=True)
        path.write_text('{"event_kind":"bad","tenant_name":"Example Person"}\n', encoding="utf-8")
        attestation = gate.run_gate(local=local, hydra=hydra)
        self.assertEqual(attestation.verdict, "fail")
        self.assertTrue(any("unclassified shared fields" in failure for failure in attestation.failures))


if __name__ == "__main__":
    unittest.main()
