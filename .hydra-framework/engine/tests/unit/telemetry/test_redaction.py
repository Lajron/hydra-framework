"""Mirror tests for `hydra_engine.telemetry.redaction`."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

_SRC = Path(__file__).resolve().parents[3] / "src"
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

from hydra_engine.telemetry import redaction  # noqa: E402


TELEMETRY_FIELD_INVENTORY = {
    "at",
    "started_at",
    "ended_at",
    "generated_at",
    "session_id",
    "agent_id",
    "agent_type",
    "model",
    "models",
    "status",
    "prompt_chars",
    "result_chars",
    "total_tokens",
    "input_tokens",
    "output_tokens",
    "cache_read_tokens",
    "cache_creation_tokens",
    "turns",
    "tool_calls",
    "reads",
    "searches",
    "bash_calls",
    "duration_ms",
    "injector_matched",
    "injected",
    "subagent_path",
    "session_path",
    "subagent_records",
    "session_records",
    "data.js",
    "transcript_path",
    "transcript_rows",
    "assistant_usage_entries",
    "event_schema",
    "event_kind",
    "command_id",
    "route_result",
    "session_id_hash",
    "agent_id_hash",
}


class TelemetryRedactionContractTests(unittest.TestCase):
    def test_contract_classifies_every_field_from_inventory(self):
        missing = [field for field in sorted(TELEMETRY_FIELD_INVENTORY) if field not in redaction.FIELD_POLICIES]
        self.assertEqual(missing, [])

    def test_safe_structural_payload_keeps_only_shared_safe_fields(self):
        result = redaction.redact_shared_payload(
            {
                "at": "2026-08-24T10:00:00",
                "session_id": "session-a",
                "agent_id": "agent-1",
                "agent_type": "Explore",
                "model": "claude-sonnet-5",
                "models": ["claude-sonnet-5"],
                "status": "completed",
                "total_tokens": 117305,
                "input_tokens": 900,
                "output_tokens": 4100,
                "cache_read_tokens": 112000,
                "duration_ms": 319371,
                "injector_matched": True,
                "injected": False,
                "subagent_path": "/private/example/.hydra-framework.local/monitoring/subagent-spend.jsonl",
                "session_path": "/private/example/.hydra-framework.local/monitoring/session-spend.jsonl",
            },
            salt="repo-local-salt",
        )

        self.assertEqual(result.shared["agent_type"], "Explore")
        self.assertEqual(result.shared["total_tokens"], 117305)
        self.assertEqual(result.shared["session_id_hash"], redaction.hash_identifier("session-a", salt="repo-local-salt"))
        self.assertEqual(result.shared["agent_id_hash"], redaction.hash_identifier("agent-1", salt="repo-local-salt"))
        self.assertNotIn("session_id", result.shared)
        self.assertNotIn("agent_id", result.shared)
        self.assertNotIn("subagent_path", result.shared)
        self.assertNotIn("session_path", result.shared)
        self.assertEqual(result.private_spillover, {})

    def test_poisoned_verbatim_fields_fail_closed_to_private_spillover(self):
        result = redaction.redact_shared_payload(
            {
                "model": "claude-sonnet-5 password=HYDRA_PRIVATE_FIXTURE",
                "agent_type": "/private/example/tenant-record",
                "status": "tenant_email: person@example.invalid",
            }
        )

        self.assertEqual(result.shared, {})
        self.assertEqual(set(result.private_spillover), {"model", "agent_type", "status"})

    def test_prompt_transcript_and_command_output_are_private_only(self):
        result = redaction.redact_shared_payload(
            {
                "prompt": "please inspect tenant_id: 42",
                "transcript_rows": [{"message": {"content": "PRIVATE FILE CONTENT: room bill transfer"}}],
                "assistant_usage_entries": [{"usage": {"input_tokens": 10}}],
                "command_output": "sk-testsecret1234567890",
            }
        )

        self.assertEqual(result.shared, {})
        self.assertEqual(set(result.private_spillover), {"prompt", "transcript_rows", "assistant_usage_entries", "command_output"})

    def test_unclassified_fields_fail_closed_to_private_spillover(self):
        result = redaction.redact_shared_payload({"tenant_name": "Example Person", "total_tokens": 10})

        self.assertEqual(result.shared, {"total_tokens": 10})
        self.assertEqual(result.private_spillover, {"tenant_name": "Example Person"})

    def test_command_output_structural_fields_are_shared_safe(self):
        result = redaction.redact_shared_payload(
            {
                "provider": "claude",
                "command_head": "dotnet",
                "command_family": "dotnet-build",
                "reducer_name": "dotnet-build",
                "reducer_version": "1",
                "exit_code": 1,
                "input_line_count": 30,
                "input_char_count": 4000,
                "omitted_line_count": 25,
                "omitted_char_count": 3000,
                "had_reducer": True,
            }
        )

        self.assertEqual(result.private_spillover, {})
        self.assertEqual(result.shared["command_family"], "dotnet-build")
        self.assertEqual(result.shared["omitted_line_count"], 25)

    def test_record_arrays_and_dashboard_artifacts_never_enter_shared_rows(self):
        result = redaction.redact_shared_payload(
            {
                "subagent_records": [{"session_id": "s1", "prompt_chars": 9}],
                "session_records": [{"session_id": "s1", "total_tokens": 42}],
                "data.js": "const HYDRA_SPEND = {subagent_records: []};",
                "dashboard_data": {"subagent_records": []},
            }
        )

        self.assertEqual(result.shared, {})
        self.assertEqual(result.private_spillover, {})
        self.assertEqual(set(result.dropped), {"subagent_records", "session_records", "data.js", "dashboard_data"})

    def test_hash_fields_with_poisoned_values_are_not_hashed_into_shared_rows(self):
        result = redaction.redact_shared_payload({"session_id": "/private/example/.claude/transcript.jsonl"})

        self.assertEqual(result.shared, {})
        self.assertEqual(set(result.private_spillover), {"session_id"})


if __name__ == "__main__":
    unittest.main()
