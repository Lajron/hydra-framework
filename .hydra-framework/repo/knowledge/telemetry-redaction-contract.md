---
title: Telemetry Redaction Contract
status: active
created: 2026-08-24
owners:
  team: hydra
certainty: confirmed - the redaction test suite
provenance:
  sources:
    - .hydra-framework/engine/src/hydra_engine/telemetry/redaction.py
---

# Telemetry Redaction Contract

## Purpose

Telemetry capture is permitted only after every captured field has a
classification and a poisoned-fixture suite proves unsafe data cannot enter
shared telemetry. This page is the active field contract for local capture and
the gate that must pass before any shared telemetry default flips.

## Recommendation

Local capture writes append-only JSONL rows under
`.hydra-framework.local/telemetry/` through the unified engine writer. Capture
sites build provider-neutral typed payloads, run the redaction helper, append
the shared-safe row locally, and send failed-closed fields to private spillover.
The current provider hook mechanics are Claude-specific adapter input; the
canonical event vocabulary is not Claude-shaped.

## Classification

| Classification | Fields |
| --- | --- |
| Captured verbatim | `at`, `started_at`, `ended_at`, `generated_at`, `retention_days`, `agent_type`, `model`, `models`, `status`, `prompt_chars`, `result_chars`, `total_tokens`, `input_tokens`, `output_tokens`, `cache_read_tokens`, `cache_creation_tokens`, `turns`, `tool_calls`, `reads`, `searches`, `bash_calls`, `duration_ms`, `provider`, `command_head`, `command_family`, `reducer_name`, `reducer_version`, `exit_code`, `input_line_count`, `input_char_count`, `omitted_line_count`, `omitted_char_count`, `had_reducer`, `injector_matched`, `injected`, `event_schema`, `event_kind`, `command_id`, `route_result`, `session_id_hash`, `agent_id_hash` |
| Hashed | `session_id`, `agent_id` |
| Stripped | `hook_event_name`, `tool_name`, `tool_use_id`, `turn_id`, `permission_mode`, `cwd`, `transcript_path`, `subagent_path`, `session_path` |
| Aggregated only | `subagent_records`, `session_records` |
| Private spillover only | `prompt`, `result`, `content`, `tool_input`, `tool_response`, `raw_payload`, `transcript_text`, `transcript_rows`, `assistant_usage_entries`, `last_assistant_message`, `command_output`, `private_file_contents` |
| Dropped entirely | `data.js`, `dashboard_data`, `dashboard.html` |

Captured-verbatim fields are structural only while poison-free. If a model,
status, agent type, or other nominally structural value contains a credential,
absolute path, email, customer-shaped field, or private-file fixture marker, it
fails closed to private spillover.

Hashed fields are stored under hash-suffixed keys, for example
`session_id_hash`, so consumers cannot mistake a digest for the provider's raw
identifier. Capture code must use a private per-repository salt before any shared
row is written.

Transcript-derived session telemetry is captured only as aggregates. Provider
token names are mapped in the adapter to canonical fields such as
`cache_read_tokens` and `cache_creation_tokens`; transcript paths and rows are
not event fields. Claude `cache_read_input_tokens` maps to
`cache_read_tokens`, Claude `cache_creation_input_tokens` maps to
`cache_creation_tokens`, Codex `cached_input_tokens` maps to
`cache_read_tokens`, and Codex `cache_write_input_tokens` maps to
`cache_creation_tokens`.

Raw record arrays are not shared event rows. Shared telemetry may later publish
aggregates derived from them, or sanitized event rows built field by field, but
not raw dashboard arrays wholesale.

## Poisoned Fixtures

The synthetic redaction suite is
`.hydra-framework/engine/tests/unit/telemetry/test_redaction.py`. It covers the
fixtures for credentials, emails, customer-shaped
fields, absolute machine paths, prompt text, transcript rows, command output,
private file content markers, unknown fields, raw record arrays, and dashboard
artifacts.

The real-shape gate is `hydra.py telemetry gate`. It evaluates synthetic event
fixtures plus locally captured typed rows, injects poison into real event
fields, and emits a committable JSON attestation with event counts, distinct
field names, the `redaction.py` digest, verdict, and date. A local run on
2026-08-28 reported 25 events, 3 distinct event kinds, 22 distinct field names,
0/1000 spillover, verdict `pass`, and redaction digest
`ecedc3f3543cfff238567568f22fafd9c48c242933fc364016d7ba08726e6fde`.

## Sources

- `.hydra-framework/engine/src/hydra_engine/telemetry/redaction.py`
- `.hydra-framework/engine/src/hydra_engine/telemetry/writer.py`
- `.hydra-framework/engine/src/hydra_engine/telemetry/gate.py`
- `.hydra-framework/engine/src/hydra_engine/telemetry/transcripts.py`
