"""Mirror tests for `hydra_engine.telemetry.transcripts`."""

from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

_SRC = Path(__file__).resolve().parents[3] / "src"
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

from hydra_engine.telemetry import transcripts, writer  # noqa: E402


class TranscriptAggregateTests(unittest.TestCase):
    def test_maps_claude_usage_names_to_canonical_token_fields(self):
        root = Path(tempfile.mkdtemp(prefix="telemetry-transcripts-"))
        transcript = root / "claude.jsonl"
        transcript.write_text(
            json.dumps(
                {
                    "message": {
                        "model": "claude-sonnet",
                        "usage": {
                            "input_tokens": 10,
                            "output_tokens": 20,
                            "cache_read_input_tokens": 30,
                            "cache_creation_input_tokens": 40,
                        },
                    }
                }
            )
            + "\n",
            encoding="utf-8",
        )
        event = transcripts.claude_session_aggregate(transcript, provider="claude", session_id="s1")
        self.assertIsNotNone(event)
        assert event is not None
        self.assertEqual(event["cache_read_tokens"], 30)
        self.assertEqual(event["cache_creation_tokens"], 40)
        self.assertEqual(event["total_tokens"], 100)
        self.assertNotIn("transcript_path", event)

    def test_hook_payload_capture_writes_aggregate_without_path(self):
        root = Path(tempfile.mkdtemp(prefix="telemetry-transcripts-capture-"))
        transcript = root / "claude.jsonl"
        transcript.write_text(json.dumps({"usage": {"prompt_tokens": 3, "completion_tokens": 4}}) + "\n", encoding="utf-8")
        local = root / ".hydra-framework.local"
        transcripts.capture_claude_session_aggregate(local, {"transcript_path": str(transcript), "session_id": "s1"})
        rows = list(writer.iter_event_rows(local))
        self.assertEqual(rows[0]["event_kind"], "session.aggregate")
        self.assertEqual(rows[0]["input_tokens"], 3)
        self.assertNotIn("transcript_path", rows[0])

    def test_maps_codex_token_count_names_to_canonical_token_fields(self):
        root = Path(tempfile.mkdtemp(prefix="telemetry-transcripts-codex-"))
        transcript = root / "codex.jsonl"
        transcript.write_text(
            json.dumps(
                {
                    "type": "event_msg",
                    "payload": {
                        "type": "token_count",
                        "model": "gpt-5-codex",
                        "info": {
                            "last_token_usage": {
                                "input_tokens": 11,
                                "output_tokens": 22,
                                "cached_input_tokens": 33,
                                "cache_write_input_tokens": 44,
                                "reasoning_output_tokens": 55,
                            }
                        },
                    },
                }
            )
            + "\n",
            encoding="utf-8",
        )
        event = transcripts.codex_session_aggregate(transcript, provider="codex", session_id="s1")
        self.assertIsNotNone(event)
        assert event is not None
        self.assertEqual(event["cache_read_tokens"], 33)
        self.assertEqual(event["cache_creation_tokens"], 44)
        self.assertEqual(event["total_tokens"], 110)
        self.assertEqual(event["model"], "gpt-5-codex")
        self.assertNotIn("transcript_path", event)
        self.assertNotIn("cached_input_tokens", event)
        self.assertNotIn("cache_write_input_tokens", event)

    def test_codex_hook_payload_capture_accepts_session_path_without_storing_it(self):
        root = Path(tempfile.mkdtemp(prefix="telemetry-transcripts-codex-capture-"))
        transcript = root / "codex.jsonl"
        transcript.write_text(
            json.dumps({"payload": {"type": "token_count", "info": {"last_token_usage": {"input_tokens": 5, "output_tokens": 6}}}})
            + "\n",
            encoding="utf-8",
        )
        local = root / ".hydra-framework.local"
        transcripts.capture_codex_session_aggregate(local, {"session_path": str(transcript), "session_id": "s1"})
        rows = list(writer.iter_event_rows(local))
        self.assertEqual(rows[0]["event_kind"], "session.aggregate")
        self.assertEqual(rows[0]["provider"], "codex")
        self.assertEqual(rows[0]["input_tokens"], 5)
        self.assertNotIn("session_path", rows[0])


if __name__ == "__main__":
    unittest.main()
