"""Mirror test for `hydra_engine.checks.task_contract_docs`."""

from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

_SRC = Path(__file__).resolve().parents[3] / "src"
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

from hydra_engine.checks import task_contract_docs  # noqa: E402

SECTIONS = ["Owner:", "## Goal"]


class ValidateTaskContractDocsTests(unittest.TestCase):
    def _hydra(self) -> tuple[Path, Path]:
        root = Path(tempfile.mkdtemp(prefix="task-contract-docs-test-"))
        hydra = root / ".hydra-framework"
        hydra.mkdir()
        return hydra, root

    def test_absent_docs_are_not_an_error(self) -> None:
        hydra, root = self._hydra()
        self.assertEqual(task_contract_docs.validate_task_contract_docs(hydra, root, SECTIONS), [])

    def test_template_missing_a_required_section_is_reported(self) -> None:
        hydra, root = self._hydra()
        template = hydra / "tasks/templates/task.md"
        template.parent.mkdir(parents=True)
        template.write_text("Owner: x\n", encoding="utf-8")
        findings = task_contract_docs.validate_task_contract_docs(hydra, root, SECTIONS)
        self.assertEqual(len(findings), 1)
        self.assertIn("missing `## Goal` required by validate", findings[0])

    def test_workflow_doc_not_describing_a_section_is_reported(self) -> None:
        hydra, root = self._hydra()
        workflow = hydra / "capabilities/workflows/task-lifecycle.md"
        workflow.parent.mkdir(parents=True)
        workflow.write_text("this document says nothing about who is responsible\n", encoding="utf-8")
        findings = task_contract_docs.validate_task_contract_docs(hydra, root, SECTIONS)
        self.assertTrue(any("does not describe `owner`" in f for f in findings))

    def test_complete_docs_report_nothing(self) -> None:
        hydra, root = self._hydra()
        template = hydra / "tasks/templates/task.md"
        template.parent.mkdir(parents=True)
        template.write_text("Owner: x\n\n## Goal\n", encoding="utf-8")
        workflow = hydra / "capabilities/workflows/task-lifecycle.md"
        workflow.parent.mkdir(parents=True)
        workflow.write_text("Every record names an owner and a goal.\n", encoding="utf-8")
        self.assertEqual(task_contract_docs.validate_task_contract_docs(hydra, root, SECTIONS), [])


if __name__ == "__main__":
    unittest.main()
