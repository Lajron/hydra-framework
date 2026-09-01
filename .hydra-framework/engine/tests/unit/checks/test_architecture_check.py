"""Mirror test for `hydra_engine.checks.architecture_check`."""

from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

_SRC = Path(__file__).resolve().parents[3] / "src"
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

from hydra_engine.checks import architecture_check  # noqa: E402
from hydra_engine.finding import Finding  # noqa: E402


class ValidateArchitectureTests(unittest.TestCase):
    def _package(self) -> Path:
        tmp = Path(tempfile.mkdtemp(prefix="architecture-check-test-"))
        package_root = tmp / "src" / "hydra_engine"
        package_root.mkdir(parents=True)
        return package_root

    def test_clean_package_reports_nothing(self) -> None:
        package_root = self._package()
        (package_root / "documents").mkdir()
        (package_root / "documents" / "tokens.py").write_text("x = 1\n", encoding="utf-8")
        findings = architecture_check.validate_architecture(
            package_root=package_root, test_unit_root=None,
            hydra_shim=None, repo_root=package_root.parent.parent,
        )
        self.assertEqual(findings, [])

    def test_boundary_name_violation_becomes_a_finding(self) -> None:
        package_root = self._package()
        (package_root / "util").mkdir()
        (package_root / "util" / "helpers.py").write_text("x = 1\n", encoding="utf-8")
        findings = architecture_check.validate_architecture(
            package_root=package_root, test_unit_root=package_root.parent.parent / "tests" / "unit",
            hydra_shim=package_root.parent.parent / "shim.py", repo_root=package_root.parent.parent,
        )
        self.assertTrue(findings)
        self.assertTrue(all(isinstance(f, Finding) for f in findings))
        self.assertTrue(any(f.code.startswith("architecture:boundary-names") for f in findings))
        self.assertTrue(any("banned name" in f.detail for f in findings))


class ValidateNoChecksImportStoreTests(unittest.TestCase):
    def _package(self) -> Path:
        tmp = Path(tempfile.mkdtemp(prefix="architecture-check-store-boundary-"))
        package_root = tmp / "src" / "hydra_engine"
        package_root.mkdir(parents=True)
        return package_root

    def test_checks_module_importing_the_store_becomes_a_finding(self) -> None:
        package_root = self._package()
        (package_root / "checks").mkdir()
        (package_root / "checks" / "object_model.py").write_text(
            "from hydra_engine.objects.store_queries import resolve\nx = resolve\n", encoding="utf-8",
        )
        findings = architecture_check.validate_no_checks_import_store(package_root=package_root)
        self.assertTrue(findings)
        self.assertTrue(all(isinstance(f, Finding) for f in findings))
        self.assertTrue(any(f.code == "architecture:validation-boundary" for f in findings))
        self.assertTrue(any("store_queries" in f.detail for f in findings))

    def test_checks_module_importing_an_ordinary_module_reports_nothing(self) -> None:
        package_root = self._package()
        (package_root / "checks").mkdir()
        (package_root / "checks" / "object_model.py").write_text(
            "from hydra_engine.objects.references import validate_object_references\nx = validate_object_references\n",
            encoding="utf-8",
        )
        self.assertEqual(architecture_check.validate_no_checks_import_store(package_root=package_root), [])

    def test_a_non_checks_module_importing_the_store_reports_nothing(self) -> None:
        package_root = self._package()
        (package_root / "commands").mkdir()
        (package_root / "commands" / "store.py").write_text(
            "from hydra_engine.objects.store_build import rebuild_store\nx = rebuild_store\n", encoding="utf-8",
        )
        self.assertEqual(architecture_check.validate_no_checks_import_store(package_root=package_root), [])


if __name__ == "__main__":
    unittest.main()
