"""Mirror tests for `hydra_engine.telemetry.writer`."""

from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

_SRC = Path(__file__).resolve().parents[3] / "src"
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

from hydra_engine.telemetry import writer  # noqa: E402


def _local() -> Path:
    return Path(tempfile.mkdtemp(prefix="telemetry-writer-")) / ".hydra-framework.local"


class TelemetryWriterTests(unittest.TestCase):
    def test_writes_shared_safe_rows_under_unified_telemetry_directory(self):
        local = _local()
        writer.write_event(local, {"event_kind": "command.invocation", "command_id": "validate"})
        rows = list(writer.iter_event_rows(local))
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["event_kind"], "command.invocation")
        self.assertEqual(rows[0]["command_id"], "validate")
        self.assertTrue(writer.events_path(local).is_file())

    def test_spills_unsafe_structural_values_to_private_spillover(self):
        local = _local()
        result = writer.write_event(local, {"event_kind": "command.invocation", "command_id": "password=HYDRA_PRIVATE_FIXTURE"})
        self.assertNotIn("command_id", result.shared)
        self.assertEqual(set(result.private_spillover), {"command_id"})
        self.assertTrue(writer.spillover_path(local).is_file())


class KnowledgeAggregationTests(unittest.TestCase):
    def test_knowledge_events_aggregate_at_read_time_from_new_rows(self):
        local = _local()
        writer.record_knowledge_command_usage(local, "knowledge-search")
        writer.record_knowledge_command_usage(local, "knowledge-search")
        writer.record_knowledge_route(local, True)
        writer.record_knowledge_route(local, False)
        counts = writer.knowledge_counts(local)
        self.assertEqual(counts["commands"]["knowledge-search"], 2)
        self.assertEqual(counts["route"], {"hit": 1, "miss": 1})

    def test_route_event_carries_routing_evidence_fields(self):
        local = _local()
        writer.record_knowledge_route(
            local, True, package_count=2, match_reason="routing keyword", reference_count=1, suppressed=True,
        )
        rows = list(writer.iter_event_rows(local))
        self.assertEqual(rows[0]["package_count"], 2)
        self.assertEqual(rows[0]["match_reason"], "routing keyword")
        self.assertEqual(rows[0]["reference_count"], 1)
        self.assertEqual(rows[0]["suppressed"], True)

    def test_route_event_defaults_match_reason_to_none(self):
        local = _local()
        writer.record_knowledge_route(local, False)
        rows = list(writer.iter_event_rows(local))
        self.assertEqual(rows[0]["match_reason"], "none")

    def test_malformed_event_line_is_skipped(self):
        local = _local()
        path = writer.events_path(local)
        path.parent.mkdir(parents=True)
        path.write_text("not json\n", encoding="utf-8")
        self.assertEqual(writer.knowledge_counts(local), {})

    def test_growth_note_uses_unified_event_log(self):
        root = Path(tempfile.mkdtemp(prefix="telemetry-growth-"))
        local = root / ".hydra-framework.local"
        for _ in range(2):
            writer.record_knowledge_command_usage(local, "knowledge-search")
        notes = writer.event_growth_notes(local, root, growth_advisory_lines=1)
        self.assertEqual(len(notes), 1)
        self.assertIn("telemetry/events.jsonl", notes[0])


if __name__ == "__main__":
    unittest.main()
