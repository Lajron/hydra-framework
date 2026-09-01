"""Mirror test for `hydra_engine.telemetry.reporting`."""

from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

_SRC = Path(__file__).resolve().parents[3] / "src"
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

from hydra_engine.telemetry import reporting, writer  # noqa: E402


def _local() -> Path:
    return Path(tempfile.mkdtemp(prefix="telemetry-reporting-")) / ".hydra-framework.local"


class BuildReportTests(unittest.TestCase):
    def test_empty_corpus_reports_zero(self):
        report = reporting.build_report(_local())
        self.assertEqual(report["event_count"], 0)
        self.assertEqual(report["distinct_event_kinds"], 0)
        self.assertEqual(report["counts_by_kind"], {})
        self.assertNotIn("reducer_coverage", report)

    def test_counts_events_by_kind(self):
        local = _local()
        writer.record_command_invocation(local, "validate")
        writer.record_command_invocation(local, "doctor")
        writer.record_knowledge_route(local, True)
        report = reporting.build_report(local)
        self.assertEqual(report["event_count"], 3)
        self.assertEqual(report["counts_by_kind"]["command.invocation"], 2)
        self.assertEqual(report["counts_by_kind"]["knowledge.route"], 1)
        self.assertIn("command.invocation", report["event_kinds"])
        self.assertIn("event_kind", report["field_names"])

    def test_knowledge_counts_are_folded_in(self):
        local = _local()
        writer.record_knowledge_command_usage(local, "search")
        writer.record_knowledge_route(local, False)
        report = reporting.build_report(local)
        self.assertEqual(report["knowledge_commands"], {"search": 1})
        self.assertEqual(report["knowledge_route"], {"miss": 1})

    def test_reducer_coverage_is_present_only_when_measured(self):
        local = _local()
        writer.write_event(local, {
            "event_kind": "command_output.reducer_outcome",
            "provider": "claude",
            "command_head": "dotnet",
            "exit_code": 0,
            "command_family": "dotnet-build",
            "reducer_name": "dotnet-build",
            "reducer_version": "1",
            "had_reducer": True,
        })
        writer.write_event(local, {
            "event_kind": "command_output.reducer_outcome",
            "provider": "claude",
            "command_head": "make",
            "exit_code": 0,
            "command_family": "unknown",
            "had_reducer": False,
        })
        report = reporting.build_report(local)
        self.assertEqual(report["reducer_coverage"], {"total": 2, "had_reducer": 1, "no_reducer": 1})

    def test_report_shape_has_no_raw_row_keys(self):
        # The report must be safe to paste directly into `metrics.json`.
        local = _local()
        writer.record_command_invocation(local, "validate")
        report = reporting.build_report(local)
        self.assertNotIn("event_schema", report)
        for value in report.values():
            if isinstance(value, list):
                self.assertTrue(all(isinstance(item, str) for item in value))
            if isinstance(value, dict):
                self.assertTrue(all(isinstance(v, (int, float)) for v in value.values()))


if __name__ == "__main__":
    unittest.main()
