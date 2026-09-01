"""Negative tests for the architecture checker.

Each of the 8 checks gets synthetic tmp package trees that violate it, plus
at least one tree that should pass, so the checker's own correctness is
tested rather than only demonstrated once. These tests exist from
Milestone 0 onward, before any production cluster moves.
"""

from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

_SRC = Path(__file__).resolve().parents[2] / "src"
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

from hydra_engine import architecture  # noqa: E402


def _write_tree(root: Path, files: dict[str, str]) -> Path:
    for rel_path, content in files.items():
        target = root / rel_path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content)
    return root


class ArchitectureTestCase(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.tmp = Path(self._tmp.name)
        self.pkg = self.tmp / "src" / "hydra_engine"
        self.tests_unit = self.tmp / "tests" / "unit"

    def write(self, files: dict[str, str]) -> None:
        _write_tree(self.pkg, files)

    def write_tests(self, files: dict[str, str]) -> None:
        _write_tree(self.tests_unit, files)

    def run_check(self, **kwargs):
        return architecture.check(package_root=self.pkg, test_unit_root=self.tests_unit, **kwargs)

    def violations_for(self, result, check_name: str):
        return [v for v in result.violations if v.check == check_name]


class ArchitectureThresholdValueTests(unittest.TestCase):
    def test_architecture_cap_values_are_exactly_pinned(self):
        self.assertEqual(architecture.MAX_SOURCE_LINES, 400)
        self.assertEqual(architecture.MAX_TEST_LINES, 600)
        self.assertEqual(architecture.MAX_FAN_OUT, 8)
        self.assertEqual(architecture.MAX_COMPOSITION_ROOT_LINES, 200)
        self.assertEqual(architecture.HIGH_IN_DEGREE_THRESHOLD, 10)
        self.assertEqual(architecture.HIGH_IN_DEGREE_MAX_LINES, 150)


# --- Check 1: module size ----------------------------------------------------

class ModuleSizeTests(ArchitectureTestCase):
    def test_module_under_cap_passes(self):
        self.write({"documents/tokens.py": "x = 1\n"})
        self.write_tests({"documents/test_tokens.py": "from hydra_engine.documents import tokens\n\ndef test_x():\n    assert tokens.x == 1\n"})
        result = self.run_check()
        self.assertEqual(self.violations_for(result, "module-size"), [])

    def test_module_over_cap_fails(self):
        big = "x = 1\n" * (architecture.MAX_SOURCE_LINES + 1)
        self.write({"documents/tokens.py": big})
        self.write_tests({"documents/test_tokens.py": "from hydra_engine.documents import tokens\n\ndef test_x():\n    pass\n"})
        result = self.run_check()
        self.assertTrue(self.violations_for(result, "module-size"))

    def test_test_module_under_cap_passes(self):
        self.write({"documents/tokens.py": "x = 1\n"})
        self.write_tests({"documents/test_tokens.py": "from hydra_engine.documents import tokens\n\ndef test_x():\n    pass\n"})
        result = self.run_check()
        self.assertEqual(self.violations_for(result, "module-size"), [])

    def test_test_module_over_cap_fails(self):
        self.write({"documents/tokens.py": "x = 1\n"})
        big_test = "from hydra_engine.documents import tokens\n\ndef test_x():\n    pass\n" + ("# pad\n" * (architecture.MAX_TEST_LINES + 1))
        self.write_tests({"documents/test_tokens.py": big_test})
        result = self.run_check()
        self.assertTrue(self.violations_for(result, "module-size"))

    def test_grandfathered_module_below_frozen_count_passes(self):
        shim = self.tmp / "hydra.py"
        shim.write_text("x = 1\n" * 5)
        result = architecture.check(
            package_root=self.pkg, test_unit_root=self.tests_unit,
            hydra_shim=shim, grandfathered={"hydra.py": 10}, repo_root=self.tmp,
        )
        self.assertEqual(self.violations_for(result, "module-size"), [])

    def test_grandfathered_module_grown_past_frozen_count_fails(self):
        shim = self.tmp / "hydra.py"
        shim.write_text("x = 1\n" * 20)
        result = architecture.check(
            package_root=self.pkg, test_unit_root=self.tests_unit,
            hydra_shim=shim, grandfathered={"hydra.py": 10}, repo_root=self.tmp,
        )
        self.assertTrue(self.violations_for(result, "module-size"))


# --- Check 2: acyclic imports -------------------------------------------------

class AcyclicImportTests(ArchitectureTestCase):
    def test_no_cycle_passes(self):
        self.write({
            "objects/envelopes.py": "x = 1\n",
            "knowledge/packages.py": "from hydra_engine.objects import envelopes\n",
        })
        self.write_tests({
            "objects/test_envelopes.py": "from hydra_engine.objects import envelopes\n\ndef test_x():\n    pass\n",
            "knowledge/test_packages.py": "from hydra_engine.knowledge import packages\n\ndef test_x():\n    pass\n",
        })
        result = self.run_check()
        self.assertEqual(self.violations_for(result, "acyclic-imports"), [])

    def test_two_module_cycle_fails(self):
        self.write({
            "commands/a.py": "from hydra_engine.commands import b\n",
            "commands/b.py": "from hydra_engine.commands import a\n",
        })
        self.write_tests({
            "commands/test_a.py": "from hydra_engine.commands import a\n\ndef test_x():\n    pass\n",
            "commands/test_b.py": "from hydra_engine.commands import b\n\ndef test_x():\n    pass\n",
        })
        result = self.run_check()
        violations = self.violations_for(result, "acyclic-imports")
        self.assertEqual({v.module for v in violations}, {"hydra_engine.commands.a", "hydra_engine.commands.b"})

    def test_three_module_cycle_fails(self):
        self.write({
            "commands/a.py": "from hydra_engine.commands import b\n",
            "commands/b.py": "from hydra_engine.commands import c\n",
            "commands/c.py": "from hydra_engine.commands import a\n",
        })
        self.write_tests({
            "commands/test_a.py": "from hydra_engine.commands import a\n\ndef test_x():\n    pass\n",
            "commands/test_b.py": "from hydra_engine.commands import b\n\ndef test_x():\n    pass\n",
            "commands/test_c.py": "from hydra_engine.commands import c\n\ndef test_x():\n    pass\n",
        })
        result = self.run_check()
        violations = self.violations_for(result, "acyclic-imports")
        self.assertEqual(len(violations), 3)


# --- Check 3: layer direction --------------------------------------------------

class LayerDirectionTests(ArchitectureTestCase):
    def test_downward_import_passes(self):
        self.write({
            "objects/envelopes.py": "x = 1\n",
            "commands/task.py": "from hydra_engine.objects import envelopes\n",
        })
        self.write_tests({
            "objects/test_envelopes.py": "from hydra_engine.objects import envelopes\n\ndef test_x():\n    pass\n",
            "commands/test_task.py": "from hydra_engine.commands import task\n\ndef test_x():\n    pass\n",
        })
        result = self.run_check()
        self.assertEqual(self.violations_for(result, "layer-direction"), [])

    def test_sideways_import_passes(self):
        self.write({
            "knowledge/packages.py": "x = 1\n",
            "knowledge/routing.py": "from hydra_engine.knowledge import packages\n",
        })
        self.write_tests({
            "knowledge/test_packages.py": "from hydra_engine.knowledge import packages\n\ndef test_x():\n    pass\n",
            "knowledge/test_routing.py": "from hydra_engine.knowledge import routing\n\ndef test_x():\n    pass\n",
        })
        result = self.run_check()
        self.assertEqual(self.violations_for(result, "layer-direction"), [])

    def test_upward_import_fails(self):
        self.write({
            "objects/envelopes.py": "from hydra_engine.commands import task\n",
            "commands/task.py": "x = 1\n",
        })
        self.write_tests({
            "objects/test_envelopes.py": "from hydra_engine.objects import envelopes\n\ndef test_x():\n    pass\n",
            "commands/test_task.py": "from hydra_engine.commands import task\n\ndef test_x():\n    pass\n",
        })
        result = self.run_check()
        violations = self.violations_for(result, "layer-direction")
        self.assertEqual([v.module for v in violations], ["hydra_engine.objects.envelopes"])


# --- Check 4: widely-imported vocabulary ---------------------------------------

class HighInDegreeTests(ArchitectureTestCase):
    def _make_importers(self, target_import: str, count: int) -> dict[str, str]:
        return {f"commands/c{i}.py": f"from hydra_engine.identity import {target_import}\n" for i in range(count)}

    def _make_importer_tests(self, count: int) -> dict[str, str]:
        return {f"commands/test_c{i}.py": f"from hydra_engine.commands import c{i}\n\ndef test_x():\n    pass\n" for i in range(count)}

    def test_high_in_degree_leaf_vocabulary_passes(self):
        n = architecture.HIGH_IN_DEGREE_THRESHOLD + 1
        self.write({"identity/tokens.py": "x = 1\n", **self._make_importers("tokens", n)})
        self.write_tests({"identity/test_tokens.py": "from hydra_engine.identity import tokens\n\ndef test_x():\n    pass\n", **self._make_importer_tests(n)})
        result = self.run_check()
        self.assertEqual(self.violations_for(result, "widely-imported-vocabulary"), [])

    def test_high_in_degree_module_with_internal_imports_fails(self):
        n = architecture.HIGH_IN_DEGREE_THRESHOLD + 1
        self.write({"identity/tokens.py": "from hydra_engine.identity import slugs\nx = 1\n", "identity/slugs.py": "y = 1\n", **self._make_importers("tokens", n)})
        self.write_tests({
            "identity/test_tokens.py": "from hydra_engine.identity import tokens\n\ndef test_x():\n    pass\n",
            "identity/test_slugs.py": "from hydra_engine.identity import slugs\n\ndef test_x():\n    pass\n",
            **self._make_importer_tests(n),
        })
        result = self.run_check()
        self.assertTrue(self.violations_for(result, "widely-imported-vocabulary"))

    def test_high_in_degree_module_over_line_cap_fails(self):
        n = architecture.HIGH_IN_DEGREE_THRESHOLD + 1
        big = "x = 1\n" * (architecture.HIGH_IN_DEGREE_MAX_LINES + 1)
        self.write({"identity/tokens.py": big, **self._make_importers("tokens", n)})
        self.write_tests({"identity/test_tokens.py": "from hydra_engine.identity import tokens\n\ndef test_x():\n    pass\n", **self._make_importer_tests(n)})
        result = self.run_check()
        self.assertTrue(self.violations_for(result, "widely-imported-vocabulary"))


# --- Check 5: fan-out -----------------------------------------------------------

class FanOutTests(ArchitectureTestCase):
    def _leaf_modules(self, count: int) -> dict[str, str]:
        return {f"objects/leaf{i}.py": "x = 1\n" for i in range(count)}

    def _leaf_tests(self, count: int) -> dict[str, str]:
        return {f"objects/test_leaf{i}.py": f"from hydra_engine.objects import leaf{i}\n\ndef test_x():\n    pass\n" for i in range(count)}

    def test_fan_out_under_cap_passes(self):
        n = architecture.MAX_FAN_OUT
        imports = "\n".join(f"from hydra_engine.objects import leaf{i}" for i in range(n))
        self.write({"commands/wide.py": imports + "\n", **self._leaf_modules(n)})
        self.write_tests({"commands/test_wide.py": "from hydra_engine.commands import wide\n\ndef test_x():\n    pass\n", **self._leaf_tests(n)})
        result = self.run_check()
        self.assertEqual(self.violations_for(result, "fan-out"), [])

    def test_fan_out_over_cap_fails(self):
        n = architecture.MAX_FAN_OUT + 1
        imports = "\n".join(f"from hydra_engine.objects import leaf{i}" for i in range(n))
        self.write({"commands/wide.py": imports + "\n", **self._leaf_modules(n)})
        self.write_tests({"commands/test_wide.py": "from hydra_engine.commands import wide\n\ndef test_x():\n    pass\n", **self._leaf_tests(n)})
        result = self.run_check()
        self.assertTrue(self.violations_for(result, "fan-out"))

    def test_declared_composition_root_meeting_all_rules_passes(self):
        n = architecture.MAX_FAN_OUT + 3
        imports = "\n".join(f"from hydra_engine.objects import leaf{i}" for i in range(n))
        self.write({"cli/dispatch.py": imports + "\n", **self._leaf_modules(n)})
        self.write_tests({"cli/test_dispatch.py": "from hydra_engine.cli import dispatch\n\ndef test_x():\n    pass\n", **self._leaf_tests(n)})
        result = self.run_check(composition_root="hydra_engine.cli.dispatch")
        self.assertEqual(self.violations_for(result, "fan-out"), [])

    def test_composition_root_over_line_cap_fails(self):
        big = "x = 1\n" * (architecture.MAX_COMPOSITION_ROOT_LINES + 1)
        self.write({"cli/dispatch.py": big})
        self.write_tests({"cli/test_dispatch.py": "from hydra_engine.cli import dispatch\n\ndef test_x():\n    pass\n"})
        result = self.run_check(composition_root="hydra_engine.cli.dispatch")
        self.assertTrue(self.violations_for(result, "fan-out"))

    def test_composition_root_wrong_layer_fails(self):
        self.write({"commands/dispatch.py": "x = 1\n"})
        self.write_tests({"commands/test_dispatch.py": "from hydra_engine.commands import dispatch\n\ndef test_x():\n    pass\n"})
        result = self.run_check(composition_root="hydra_engine.commands.dispatch")
        self.assertTrue(self.violations_for(result, "fan-out"))

    def test_composition_root_with_nonzero_in_degree_fails(self):
        self.write({
            "cli/dispatch.py": "x = 1\n",
            "commands/task.py": "from hydra_engine.cli import dispatch\n",
        })
        self.write_tests({
            "cli/test_dispatch.py": "from hydra_engine.cli import dispatch\n\ndef test_x():\n    pass\n",
            "commands/test_task.py": "from hydra_engine.commands import task\n\ndef test_x():\n    pass\n",
        })
        result = self.run_check(composition_root="hydra_engine.cli.dispatch")
        self.assertTrue(self.violations_for(result, "fan-out"))


# --- Check 6: test mirror --------------------------------------------------------

class TestMirrorTests(ArchitectureTestCase):
    def test_every_module_mirrored_passes(self):
        self.write({"objects/envelopes.py": "x = 1\n"})
        self.write_tests({"objects/test_envelopes.py": "from hydra_engine.objects import envelopes\n\ndef test_x():\n    pass\n"})
        result = self.run_check()
        self.assertEqual(self.violations_for(result, "test-mirror"), [])

    def test_missing_test_file_fails(self):
        self.write({"objects/envelopes.py": "x = 1\n"})
        result = self.run_check()
        self.assertTrue(self.violations_for(result, "test-mirror"))

    def test_test_file_not_importing_module_fails(self):
        self.write({"objects/envelopes.py": "x = 1\n"})
        self.write_tests({"objects/test_envelopes.py": "def test_x():\n    pass\n"})
        result = self.run_check()
        self.assertTrue(self.violations_for(result, "test-mirror"))

    def test_test_file_with_no_test_defined_fails(self):
        self.write({"objects/envelopes.py": "x = 1\n"})
        self.write_tests({"objects/test_envelopes.py": "from hydra_engine.objects import envelopes\n"})
        result = self.run_check()
        self.assertTrue(self.violations_for(result, "test-mirror"))

    def test_orphan_test_module_fails(self):
        self.write({"objects/envelopes.py": "x = 1\n"})
        self.write_tests({
            "objects/test_envelopes.py": "from hydra_engine.objects import envelopes\n\ndef test_x():\n    pass\n",
            "objects/test_ghost.py": "def test_x():\n    pass\n",
        })
        result = self.run_check()
        violations = self.violations_for(result, "test-mirror")
        self.assertTrue(any("orphan" in v.detail for v in violations))


# --- Check 7: boundary names -----------------------------------------------------

class BoundaryNameTests(ArchitectureTestCase):
    def test_ordinary_names_pass(self):
        self.write({"objects/envelopes.py": "x = 1\n"})
        self.write_tests({"objects/test_envelopes.py": "from hydra_engine.objects import envelopes\n\ndef test_x():\n    pass\n"})
        result = self.run_check()
        self.assertEqual(self.violations_for(result, "boundary-names"), [])

    def test_banned_module_stem_fails(self):
        self.write({"objects/utils.py": "x = 1\n"})
        self.write_tests({"objects/test_utils.py": "from hydra_engine.objects import utils\n\ndef test_x():\n    pass\n"})
        result = self.run_check()
        self.assertTrue(self.violations_for(result, "boundary-names"))

    def test_banned_directory_component_fails(self):
        self.write({"runtime/context.py": "x = 1\n"})
        self.write_tests({"runtime/test_context.py": "from hydra_engine.runtime import context\n\ndef test_x():\n    pass\n"})
        result = self.run_check()
        self.assertTrue(self.violations_for(result, "boundary-names"))


# --- Check 8: root derivation locality --------------------------------------------

class RootDerivationTests(ArchitectureTestCase):
    def test_docstring_mention_of_path_passes(self):
        self.write({"objects/envelopes.py": '"""Uses .hydra-framework/scripts/hydra.py as an example path."""\nx = 1\n'})
        self.write_tests({"objects/test_envelopes.py": "from hydra_engine.objects import envelopes\n\ndef test_x():\n    pass\n"})
        result = self.run_check()
        self.assertEqual(self.violations_for(result, "root-derivation-locality"), [])

    def test_file_dunder_parents_subscript_fails(self):
        self.write({"objects/envelopes.py": "from pathlib import Path\nROOT = Path(__file__).resolve().parents[3]\n"})
        self.write_tests({"objects/test_envelopes.py": "from hydra_engine.objects import envelopes\n\ndef test_x():\n    pass\n"})
        result = self.run_check()
        self.assertTrue(self.violations_for(result, "root-derivation-locality"))

    def test_chained_parent_walk_fails(self):
        self.write({"objects/envelopes.py": "from pathlib import Path\nROOT = Path(__file__).parent.parent.parent\n"})
        self.write_tests({"objects/test_envelopes.py": "from hydra_engine.objects import envelopes\n\ndef test_x():\n    pass\n"})
        result = self.run_check()
        self.assertTrue(self.violations_for(result, "root-derivation-locality"))

    def test_composition_root_is_exempt(self):
        self.write({"cli/dispatch.py": "from pathlib import Path\nROOT = Path(__file__).resolve().parents[3]\n"})
        self.write_tests({"cli/test_dispatch.py": "from hydra_engine.cli import dispatch\n\ndef test_x():\n    pass\n"})
        result = self.run_check(composition_root="hydra_engine.cli.dispatch")
        self.assertEqual(self.violations_for(result, "root-derivation-locality"), [])


if __name__ == "__main__":
    unittest.main()
