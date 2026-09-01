"""Provider-surface findings for `validate`.

`providers.reclaim.classify_surfaces` itself is not part of the `validate_*`
family (it is not named `validate_*`, and Target Structure rule 2 scopes the
Finding conversion to that family deliberately) and keeps returning
`list[dict]` unchanged -- `command_doctor`'s own surface report still reads
those dicts directly. This module only takes over the per-item formatting
`command_validate` used to do inline, unchanged, so the aggregator does not
need to know provider-surface shape at all.
"""

from __future__ import annotations

from hydra_engine.finding import Finding


def provider_surface_findings(surfaces: list[dict[str, str]]) -> list[Finding]:
    return [
        Finding(
            path=item["path"],
            code="provider-surface",
            detail=f"{item['path']}: {item['status']} provider surface: {item['detail']}",
        )
        for item in surfaces
        if item["status"] != "generated"
    ]
