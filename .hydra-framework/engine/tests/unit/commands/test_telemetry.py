"""Mirror test for `hydra_engine.commands.telemetry`."""

from __future__ import annotations

import argparse
import contextlib
import io
import json
import sys
import tempfile
import unittest
from pathlib import Path

_SRC = Path(__file__).resolve().parents[3] / "src"
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

from hydra_engine.cli import dispatch  # noqa: E402
from hydra_engine.commands import telemetry  # noqa: E402


class TelemetryCommandTests(unittest.TestCase):
    def test_gate_prints_committable_attestation_json(self):
        root = Path(tempfile.mkdtemp(prefix="commands-telemetry-"))
        redaction_path = root / ".hydra-framework/engine/src/hydra_engine/telemetry/redaction.py"
        redaction_path.parent.mkdir(parents=True)
        redaction_path.write_text("fixture\n", encoding="utf-8")
        ctx = dispatch.RepoContext.for_root(root)
        args = argparse.Namespace(output="", max_spillover_per_1000=50, min_event_count=3, min_event_kinds=3)
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            result = telemetry.command_gate(args, ctx)
        self.assertEqual(result.exit_code, 0)
        data = json.loads(out.getvalue())
        self.assertEqual(data["verdict"], "pass")
        self.assertIn("redaction_digest", data)


if __name__ == "__main__":
    unittest.main()
