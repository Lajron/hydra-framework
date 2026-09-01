"""Tests for `hydra_engine.commands.capability`."""

from __future__ import annotations

import argparse
import contextlib
import io as stdlib_io
import sys
import tempfile
import unittest
from pathlib import Path

_SRC = Path(__file__).resolve().parents[3] / "src"
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

from hydra_engine.checks import module_metadata  # noqa: E402
from hydra_engine.commands import capability  # noqa: E402
from hydra_engine.documents.yaml_documents import parse_yaml  # noqa: E402
from hydra_engine.providers.paths import ProvidersPaths  # noqa: E402


def _paths() -> ProvidersPaths:
    root = Path(tempfile.mkdtemp(prefix="commands-capability-"))
    return ProvidersPaths(root=root, hydra=root / ".hydra-framework")


class CapabilityScaffoldTests(unittest.TestCase):
    def test_creates_skill_with_valid_metadata(self):
        paths = _paths()
        args = argparse.Namespace(name="demo-skill", description="Demo skill.", kind="procedure", title="", force=False)
        with contextlib.redirect_stdout(stdlib_io.StringIO()):
            result = capability.command_capability_scaffold_skill(args, paths)
        self.assertEqual(result.exit_code, 0)
        metadata_path = paths.skills_root() / "demo-skill" / "metadata.yaml"
        self.assertTrue((paths.skills_root() / "demo-skill" / "skill.md").exists())
        entry = module_metadata.ModuleMetadataEntry(
            module_dir=metadata_path.parent,
            metadata_path=metadata_path,
            required=["name", "description"],
            is_skill=True,
            data=parse_yaml(metadata_path, paths.root),
            parse_error=None,
        )
        self.assertEqual(module_metadata.validate_module_metadata([entry], paths.root), [])

    def test_creates_agent(self):
        paths = _paths()
        args = argparse.Namespace(name="demo-agent", description="Demo agent.", capability_class="fast-default", effort="standard", title="", force=False)
        with contextlib.redirect_stdout(stdlib_io.StringIO()):
            result = capability.command_capability_scaffold_agent(args, paths)
        self.assertEqual(result.exit_code, 0)
        self.assertTrue((paths.agents_root() / "demo-agent" / "agent.md").exists())
        metadata = parse_yaml(paths.agents_root() / "demo-agent" / "metadata.yaml", paths.root)
        self.assertEqual(metadata["capability_class"], "fast-default")
        self.assertEqual(metadata["effort"], "standard")

    def test_refuses_existing_module_without_force(self):
        paths = _paths()
        target = paths.skills_root() / "demo-skill"
        target.mkdir(parents=True)
        (target / "skill.md").write_text("existing\n", encoding="utf-8")
        args = argparse.Namespace(name="demo-skill", description="Demo skill.", kind="procedure", title="", force=False)
        with contextlib.redirect_stdout(stdlib_io.StringIO()) as out:
            result = capability.command_capability_scaffold_skill(args, paths)
        self.assertEqual(result.exit_code, 1)
        self.assertIn("already exists", out.getvalue())

    def test_force_overwrites_module_files(self):
        paths = _paths()
        target = paths.agents_root() / "demo-agent"
        target.mkdir(parents=True)
        (target / "agent.md").write_text("existing\n", encoding="utf-8")
        args = argparse.Namespace(name="demo-agent", description="Demo agent.", capability_class="fast-default", effort="standard", title="", force=True)
        with contextlib.redirect_stdout(stdlib_io.StringIO()):
            result = capability.command_capability_scaffold_agent(args, paths)
        self.assertEqual(result.exit_code, 0)
        self.assertIn("# Demo Agent", (target / "agent.md").read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
