"""Mirror test for `hydra_engine.checks.module_metadata`."""

from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

_SRC = Path(__file__).resolve().parents[3] / "src"
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

from hydra_engine.checks import module_metadata  # noqa: E402


class ValidateModuleMetadataTests(unittest.TestCase):
    def _entry(self, **overrides) -> module_metadata.ModuleMetadataEntry:
        root = Path(tempfile.mkdtemp(prefix="module-metadata-test-"))
        defaults = dict(
            module_dir=root / "capabilities/skills/example",
            metadata_path=root / "capabilities/skills/example/metadata.yaml",
            required=["name", "description"],
            is_skill=True,
            data={"name": "example", "description": "does a thing"},
            parse_error=None,
        )
        defaults.update(overrides)
        return module_metadata.ModuleMetadataEntry(**defaults), root

    def test_complete_entry_reports_nothing(self) -> None:
        entry, root = self._entry()
        self.assertEqual(module_metadata.validate_module_metadata([entry], root), [])

    def test_missing_metadata_file_is_reported(self) -> None:
        entry, root = self._entry(data=None, parse_error=None)
        findings = module_metadata.validate_module_metadata([entry], root)
        self.assertEqual(len(findings), 1)
        self.assertIn("missing metadata.yaml", findings[0])

    def test_parse_error_is_reported_verbatim(self) -> None:
        entry, root = self._entry(data=None, parse_error="capabilities/skills/example/metadata.yaml: file not found")
        findings = module_metadata.validate_module_metadata([entry], root)
        self.assertEqual([str(f) for f in findings], ["capabilities/skills/example/metadata.yaml: file not found"])

    def test_missing_required_key_is_reported(self) -> None:
        entry, root = self._entry(data={"name": "example"})
        findings = module_metadata.validate_module_metadata([entry], root)
        self.assertEqual(len(findings), 1)
        self.assertIn("missing `description`", findings[0])

    def test_skill_kind_must_be_procedure_or_command(self) -> None:
        entry, root = self._entry(data={"name": "example", "description": "x", "kind": "persona"})
        findings = module_metadata.validate_module_metadata([entry], root)
        self.assertEqual(len(findings), 1)
        self.assertIn("`kind` must be `procedure` or `command`, got `persona`", findings[0])

    def test_agent_kind_is_not_checked(self) -> None:
        entry, root = self._entry(
            required=["name", "description", "capability_class", "effort"],
            is_skill=False,
            data={"name": "a", "description": "x", "capability_class": "local-private", "effort": "standard", "kind": "persona"},
        )
        self.assertEqual(module_metadata.validate_module_metadata([entry], root), [])


if __name__ == "__main__":
    unittest.main()
