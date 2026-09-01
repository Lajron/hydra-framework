"""Derived aggregates over the private telemetry corpus.

The only way to get numbers for a telemetry evidence package's `metrics.json`
without hand-reading `.hydra-framework.local/telemetry/events.jsonl`. Every
bucket here is exactly one `telemetry.evidence`'s `metrics.json` validator
accepts: scalar counts, flat per-kind count maps, and name lists -- never a
raw row, so a package built from this report's `--json` output cannot
accidentally paste one.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from hydra_engine.ports import clock
from hydra_engine.telemetry import writer

_REDUCER_OUTCOME_KIND = "command_output.reducer_outcome"


def build_report(local: Path) -> dict[str, Any]:
    rows = list(writer.iter_event_rows(local))

    event_kinds: list[str] = []
    field_names: set[str] = set()
    counts_by_kind: dict[str, int] = {}
    reducer_total = 0
    reducer_had = 0

    for row in rows:
        field_names.update(row)
        kind = row.get("event_kind")
        if isinstance(kind, str) and kind:
            counts_by_kind[kind] = counts_by_kind.get(kind, 0) + 1
            if kind == _REDUCER_OUTCOME_KIND:
                reducer_total += 1
                if row.get("had_reducer"):
                    reducer_had += 1

    report: dict[str, Any] = {
        "generated_at": clock.now_utc_iso(),
        "event_count": len(rows),
        "distinct_event_kinds": len(counts_by_kind),
        "distinct_field_names": len(field_names),
        "event_kinds": sorted(counts_by_kind),
        "field_names": sorted(field_names),
        "counts_by_kind": counts_by_kind,
    }

    knowledge = writer.knowledge_counts(local)
    if "commands" in knowledge:
        report["knowledge_commands"] = knowledge["commands"]
    if "route" in knowledge:
        report["knowledge_route"] = knowledge["route"]

    if reducer_total:
        report["reducer_coverage"] = {
            "total": reducer_total,
            "had_reducer": reducer_had,
            "no_reducer": reducer_total - reducer_had,
        }

    return report
