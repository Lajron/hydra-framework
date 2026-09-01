"""Mirror test for `hydra_engine.checks.package_and_task_findings`."""

from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

_SRC = Path(__file__).resolve().parents[3] / "src"
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

from hydra_engine.checks import package_and_task_findings  # noqa: E402
from hydra_engine.cli.dispatch import RepoContext  # noqa: E402


def _ctx() -> RepoContext:
    root = Path(tempfile.mkdtemp(prefix="package-task-findings-test-"))
    (root / ".hydra-framework").mkdir(parents=True)
    return RepoContext.for_root(root)


class TaskRecordsCheckTests(unittest.TestCase):
    def test_no_tasks_is_clean(self):
        self.assertEqual(package_and_task_findings.task_records_check(_ctx()), [])


class ProviderSurfacesCheckTests(unittest.TestCase):
    def test_no_surfaces_is_clean(self):
        self.assertEqual(package_and_task_findings.provider_surfaces_check(_ctx()), [])


class PackageDocsCheckTests(unittest.TestCase):
    def test_no_packages_is_clean(self):
        self.assertEqual(package_and_task_findings.package_docs_check(_ctx()), [])


class FlatKnowledgeCheckTests(unittest.TestCase):
    def test_no_flat_knowledge_is_clean(self):
        self.assertEqual(package_and_task_findings.flat_knowledge_check(_ctx()), [])


if __name__ == "__main__":
    unittest.main()
