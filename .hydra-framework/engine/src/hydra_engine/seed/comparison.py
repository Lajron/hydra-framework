"""Classify mechanical framework differences as explained or unexplained."""

from __future__ import annotations

from hydra_engine.seed.adaptations import ledger_entries_for_path

# Adoption and recording necessarily rewrite these two files, so a difference
# here is structural rather than drift. Without this, every adopted copy would
# report two permanent unexplained differences and `--fail-on-drift` could never
# pass. The cost is that other manifest edits are not flagged either; the
# manifest is descriptive, and `adopt --record` is its documented writer.
EXPECTED_LOCAL_DIVERGENCE = {
    "manifest.yaml": "expected: lineage stamped by `adopt --record`",
    "evolution/adaptations.md": "expected: the adaptation ledger itself",
}


def schema_drift_reason(path: str, schema_drift: dict[str, str]) -> list[str]:
    reason = schema_drift.get(path)
    return [reason] if reason else []


def split_differences_by_adaptation(
    rows: dict[str, list[str]],
    entries: list[dict],
    schema_drift: dict[str, str] | None = None,
) -> dict[str, list[dict]]:
    """Separate deliberate divergence from drift, so reconciliation only looks at
    what nobody has explained yet.

    `schema_drift` maps a `local-modified` path to an explanation when the
    only reason it differs from base is that its envelope is behind the
    base's `schema_version` (the first resolved architecture gap): "two envelope versions
    behind" is a known, actionable state, not unexplained drift.
    """
    schema_drift = schema_drift or {}
    split: dict[str, list[dict]] = {"explained": [], "unexplained": []}
    for label in ["local-modified", "local-only", "base-only"]:
        for path in rows.get(label, []):
            reasons = ledger_entries_for_path(path, entries)
            if not reasons and path in EXPECTED_LOCAL_DIVERGENCE:
                reasons = [EXPECTED_LOCAL_DIVERGENCE[path]]
            if not reasons and label == "local-modified":
                reasons = schema_drift_reason(path, schema_drift)
            item = {"path": path, "mechanical": label, "explained_by": reasons}
            split["explained" if reasons else "unexplained"].append(item)
    return split
