"""Mirror tests for `hydra_engine.command_output.registry`."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

_SRC = Path(__file__).resolve().parents[3] / "src"
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

from hydra_engine.command_output import registry  # noqa: E402
from hydra_engine.command_output.model import CommandOutput  # noqa: E402


class RegistryTests(unittest.TestCase):
    def test_registered_reducer_names_are_unique(self):
        self.assertEqual(len(registry.REDUCERS), len(registry.REDUCERS_BY_NAME))

    def test_reducer_for_command_uses_explicit_registry(self):
        self.assertEqual(registry.reducer_for_command("cd src && dotnet build").name, "dotnet-build")

    def test_unknown_command_returns_unknown_reduction(self):
        reduction = registry.reduce_command_output(CommandOutput("manual", "", "custom-tool", ".", 0, "line"), 10)
        self.assertEqual(reduction.family, "unknown")
        self.assertFalse(reduction.has_reducer)


if __name__ == "__main__":
    unittest.main()

