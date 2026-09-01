"""Mirror test for `hydra_engine.providers.adapter_plan`."""

from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

_SRC = Path(__file__).resolve().parents[3] / "src"
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

from hydra_engine.providers.adapter_plan import planned_adapter_files  # noqa: E402
from hydra_engine.providers.paths import ProvidersPaths  # noqa: E402


def _write(root: Path, rel: str, content: str) -> None:
    target = root / rel
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(content, encoding="utf-8")


def _paths_with_one_skill() -> ProvidersPaths:
    root = Path(tempfile.mkdtemp(prefix="providers-adapter-plan-"))
    _write(
        root,
        ".hydra-framework/capabilities/skills/demo-skill/metadata.yaml",
        "name: demo-skill\ndescription: Use when relevant.\nkind: procedure\n",
    )
    _write(root, ".hydra-framework/capabilities/skills/demo-skill/skill.md", "# Demo Skill\n\nBody.\n")
    return ProvidersPaths(root=root, hydra=root / ".hydra-framework")


class PlannedAdapterFilesTests(unittest.TestCase):
    def test_plans_a_skill_wrapper_for_every_adapter_target(self):
        paths = _paths_with_one_skill()
        plan = planned_adapter_files(paths)
        claude_skill = paths.root / ".claude/skills/hydra-demo-skill/SKILL.md"
        codex_skill = paths.root / ".agents/skills/hydra-demo-skill/SKILL.md"
        self.assertIn(claude_skill, plan)
        self.assertIn(codex_skill, plan)
        self.assertIn("# Demo Skill", plan[claude_skill])

    def test_every_generated_body_has_a_provenance_sidecar(self):
        paths = _paths_with_one_skill()
        plan = planned_adapter_files(paths)
        bodies = [path for path in plan if path.name == "SKILL.md"]
        self.assertTrue(bodies)
        for body in bodies:
            sidecar = body.parent / ".hydra-adapter.yaml"
            self.assertIn(sidecar, plan)
            self.assertIn("canonical_source: .hydra-framework/capabilities/skills/demo-skill/skill.md", plan[sidecar])

    def test_empty_modules_produce_an_empty_plan(self):
        root = Path(tempfile.mkdtemp(prefix="providers-adapter-plan-empty-"))
        paths = ProvidersPaths(root=root, hydra=root / ".hydra-framework")
        self.assertEqual(planned_adapter_files(paths), {})

    def test_each_provider_gets_its_own_registered_agent_wrapper_form(self):
        # `PROVIDERS`' `build_agent_wrapper` field replaced an
        # `if provider == "codex":` branch here; this proves the field-based
        # dispatch still produces Codex TOML and Claude Markdown, not that
        # both providers silently got the same renderer.
        paths = _paths_with_one_skill()
        _write(
            paths.root,
            ".hydra-framework/capabilities/agents/demo-agent/metadata.yaml",
            "name: demo-agent\ndescription: Use for the role.\n",
        )
        _write(paths.root, ".hydra-framework/capabilities/agents/demo-agent/agent.md", "# Demo Agent\n\nBody.\n")
        plan = planned_adapter_files(paths)
        claude_agent = paths.root / ".claude/agents/hydra-demo-agent.md"
        codex_agent = paths.root / ".codex/agents/hydra-demo-agent.toml"
        self.assertIn(claude_agent, plan)
        self.assertIn(codex_agent, plan)
        self.assertIn("developer_instructions =", plan[codex_agent])


if __name__ == "__main__":
    unittest.main()
