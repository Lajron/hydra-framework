"""Threshold registry coverage and exact-value pins."""

from __future__ import annotations

import ast
import importlib
import sys
import unittest
from pathlib import Path

_SRC = Path(__file__).resolve().parents[2] / "src"
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

from hydra_engine import thresholds  # noqa: E402


def _module_name(path: Path) -> str:
    rel = path.relative_to(_SRC).with_suffix("")
    parts = rel.parts
    if parts[-1] == "__init__":
        parts = parts[:-1]
    return ".".join(parts)


def _public_int_constant_names(path: Path) -> list[str]:
    tree = ast.parse(path.read_text(), filename=str(path))
    names: list[str] = []
    for node in tree.body:
        targets: list[str] = []
        value = None
        if isinstance(node, ast.Assign):
            targets = [target.id for target in node.targets if isinstance(target, ast.Name)]
            value = node.value
        elif isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name):
            targets = [node.target.id]
            value = node.value
        if not isinstance(value, ast.Constant) or not isinstance(value.value, int) or isinstance(value.value, bool):
            continue
        names.extend(name for name in targets if name.isupper() and not name.startswith("_"))
    return names


def _public_int_constant_keys() -> set[str]:
    keys: set[str] = set()
    for path in sorted((_SRC / "hydra_engine").rglob("*.py")):
        module = _module_name(path)
        if module == "hydra_engine.thresholds":
            continue
        for name in _public_int_constant_names(path):
            keys.add(f"{module}.{name}")
    return keys


class ThresholdRegistryTests(unittest.TestCase):
    def test_registry_keys_are_unique(self):
        keys = [entry.key for entry in thresholds.THRESHOLDS]
        self.assertEqual(len(keys), len(set(keys)))

    def test_registry_covers_every_public_int_constant(self):
        self.assertEqual(set(thresholds.THRESHOLDS_BY_KEY), _public_int_constant_keys())

    def test_threshold_values_are_exactly_pinned(self):
        for entry in thresholds.THRESHOLDS:
            with self.subTest(entry=entry.key):
                module = importlib.import_module(entry.module)
                self.assertEqual(getattr(module, entry.name), entry.value)

    def test_threshold_classifications_are_known(self):
        classifications = {thresholds.TEAM_TUNABLE_POLICY, thresholds.ENGINE_INVARIANT}
        for entry in thresholds.THRESHOLDS:
            with self.subTest(entry=entry.key):
                self.assertIn(entry.classification, classifications)
                self.assertTrue(entry.reason)


if __name__ == "__main__":
    unittest.main()
