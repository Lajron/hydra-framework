"""Architecture-enforcement findings for `validate`.

Wraps `hydra_engine.architecture.check()` and converts its `Violation` tuple
into `Finding`, rather than teaching `architecture.py` about `Finding`
itself: `architecture.py`'s own docstring states it is "pure AST analysis;
imports nothing from the rest of the package" (Milestone 0), and that
purity is what lets it run against synthetic tmp package trees before
`hydra_engine` holds any modules -- adding an internal import to save one
wrapper function here is not a real need. `detail` is `str(violation)`,
byte-identical to the message `validate_architecture()`'s old `list[str]`
entry held (`render()` already produces exactly that string).

`validate_no_checks_import_store` is
the mechanical enforcement of the "validation reads the export
alone" rule. It reuses `architecture.discover_modules`
rather than adding a ninth check to `architecture.py` itself: that module
sits at its own 400-line cap, and this rule is specific to `hydra_engine`'s
own package layout (`checks/`, `objects.store_*`) in a way the other eight
checks are not -- it belongs beside the wrapper that already knows
`hydra_engine`'s shape, not inside the generic, package-agnostic checker.
"""

from __future__ import annotations

from pathlib import Path

from hydra_engine import architecture
from hydra_engine.finding import Finding

# This found the one existing violation of "validation reads the
# export alone" (`knowledge/search_index.py` builds `knowledge.db` *from*
# the export, with nothing in `checks/` reading it back -- fine, but nothing
# was stopping something in `checks/` from doing exactly that). This is that
# prose rule made mechanical.
STORE_MODULE_PREFIXES = (
    "hydra_engine.objects.store_schema",
    "hydra_engine.objects.store_build",
    "hydra_engine.objects.store_queries",
    "hydra_engine.work.task_store",
)


def validate_architecture(
    *,
    package_root: Path,
    test_unit_root: Path | None,
    hydra_shim: Path | None,
    repo_root: Path | None,
    composition_root: str | None = None,
) -> list[Finding]:
    result = architecture.check(
        package_root=package_root,
        test_unit_root=test_unit_root,
        hydra_shim=hydra_shim,
        repo_root=repo_root,
        composition_root=composition_root,
    )
    return [
        Finding(path=violation.module, code=f"architecture:{violation.check}", detail=str(violation))
        for violation in result.violations
    ]


def validate_no_checks_import_store(*, package_root: Path) -> list[Finding]:
    """No module under `checks/` may import an operational-store module:
    `validate`/`ref check` reach their verdicts from the
    export alone, so a reviewer can reproduce a verdict by reading a file in
    Git rather than querying a local, untracked database."""
    modules = architecture.discover_modules(package_root, "hydra_engine")
    findings: list[Finding] = []
    for dotted, module in modules.items():
        if not dotted.startswith("hydra_engine.checks."):
            continue
        for target in sorted(module.imports):
            if target.startswith(STORE_MODULE_PREFIXES):
                findings.append(Finding(
                    path=dotted, code="architecture:validation-boundary",
                    detail=f"[validation-boundary] {dotted}: imports {target}; validation must reach its verdict from the export alone",
                ))
    return findings
