"""Check-list aggregation for `validate`/`doctor`.

`command_validate` used to import every validator domain module directly to
call it -- around 11 distinct sources feeding one aggregation, well past
check 5's fan-out cap of 8 if `commands/validation.py` imported them all
itself. Instead, whoever builds the concrete list of checks (`cli/dispatch.py`,
the composition root) imports the domain
modules and passes down a `list[Check]` as plain data -- the same
precomputed-data shape used elsewhere (e.g. `commands/hooks.py`
composing already-built `Paths` objects), just with zero-argument callables
instead of values. `commands/validation.py` itself never imports a single
domain-layer check module.
"""

from __future__ import annotations

from typing import Callable

from hydra_engine.finding import Finding

Check = Callable[[], list[Finding]]


def run_checks(checks: list[Check]) -> list[Finding]:
    findings: list[Finding] = []
    for check in checks:
        findings.extend(check())
    return findings
