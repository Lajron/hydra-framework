"""Task-record contract cross-checks.

`REQUIRED_TASK_SECTIONS` moved here from `scripts/hydra.py` once
`validate`/`doctor`'s composition itself moved into `hydra_engine.cli.dispatch`
-- this is now the one place that needs it as a literal constant rather than
a parameter, so it is the constant's canonical home. `work/task_records.py`'s
`validate_task_file` still takes `required_sections` as an explicit parameter
rather than importing this module -- `checks` (layer 3) importing down into
`work` (layer 2) would be fine, but the reverse is not, so the constant is
threaded down by the caller instead.

Converted to `Finding` per Target Structure rule 2; every `detail` string is
byte-identical to the message the old `list[str]` entry held.
"""

from __future__ import annotations

from pathlib import Path

from hydra_engine.documents.tokens import display_path, read_text
from hydra_engine.finding import Finding

# The one executable definition of task-record structure. Docs and templates
# are checked against this list so the six places that describe it cannot
# drift.
REQUIRED_TASK_SECTIONS = [
    "Owner:",
    "Updated:",
    "## Goal",
    "## Readiness",
    "Status:",
    "Branch or workspace assumptions:",
    "Relevant canonical docs:",
    "Required dependencies, services, generated artifacts, or private local requirements:",
    "Blockers and assumptions:",
    "Expected validation command or evidence:",
    "## Step State",
    "Active step:",
    "Next step:",
    "Completed steps:",
    "## Continuation Notes",
    "Running state:",
    "Resume check:",
]


def validate_task_contract_docs(hydra: Path, root: Path, required_sections: list[str]) -> list[Finding]:
    findings: list[Finding] = []
    template = hydra / "tasks/templates/task.md"
    if template.exists():
        text = read_text(template)
        path = display_path(template, root)
        for item in required_sections:
            if item not in text:
                findings.append(Finding(
                    path=path, code="task-contract-docs", detail=f"{path} missing `{item}` required by validate"
                ))
    workflow = hydra / "capabilities/workflows/task-lifecycle.md"
    if workflow.exists():
        lowered = read_text(workflow).lower()
        path = display_path(workflow, root)
        for item in required_sections:
            label = item.strip("# ").rstrip(":").lower()
            if label and label not in lowered:
                findings.append(Finding(
                    path=path, code="task-contract-docs", detail=f"{path} does not describe `{label}`"
                ))
    return findings
