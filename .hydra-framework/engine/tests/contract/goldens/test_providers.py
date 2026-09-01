"""providers goldens: export-adapters, reclaim."""

from __future__ import annotations

import unittest

from .fixtures import assert_golden, run_golden

DEMO_SKILL_FIXTURE = {
    ".hydra-framework/capabilities/skills/demo-skill/metadata.yaml": (
        "name: demo-skill\ndescription: Use when relevant.\nkind: procedure\n"
    ),
    ".hydra-framework/capabilities/skills/demo-skill/skill.md": "# Demo Skill\n\nBody.\n",
}

ORPHANED_SKILL_FIXTURE = {
    ".claude/skills/deploy/SKILL.md": '---\nname: deploy\ndescription: "Deploy the thing"\n---\nBody text.\n',
}


class ProvidersGoldenTests(unittest.TestCase):
    def test_export_adapters_happy_path(self):
        """No skills or agents to export: still a real happy path."""
        outcome = run_golden(["export-adapters"])
        assert_golden(self, "providers-export-adapters", outcome)

    def test_export_adapters_generates_a_skill_wrapper(self):
        outcome = run_golden(["export-adapters"], extra_fixture=DEMO_SKILL_FIXTURE)
        assert_golden(self, "providers-export-adapters-generated", outcome)

    def test_export_adapters_check_reports_drift(self):
        outcome = run_golden(["export-adapters", "--check"], extra_fixture=DEMO_SKILL_FIXTURE)
        assert_golden(self, "providers-export-adapters-check-drift", outcome)

    def test_reclaim_happy_path(self):
        """No provider-native files present: still a real happy path (`all
        provider files are generated`)."""
        outcome = run_golden(["reclaim"])
        assert_golden(self, "providers-reclaim", outcome)

    def test_reclaim_reports_an_orphaned_file(self):
        outcome = run_golden(["reclaim"], extra_fixture=ORPHANED_SKILL_FIXTURE)
        assert_golden(self, "providers-reclaim-orphaned", outcome)

    def test_reclaim_promote_moves_the_orphaned_file(self):
        outcome = run_golden(["reclaim", "--promote"], extra_fixture=ORPHANED_SKILL_FIXTURE)
        assert_golden(self, "providers-reclaim-promote", outcome)


if __name__ == "__main__":
    unittest.main()
