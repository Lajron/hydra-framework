"""Capability-scaffold command goldens."""

from __future__ import annotations

import unittest

from .fixtures import assert_golden, run_golden


class CapabilityGoldenTests(unittest.TestCase):
    def test_scaffold_skill(self):
        outcome = run_golden(["capability", "scaffold-skill", "demo-skill", "--description", "Demo skill."])
        assert_golden(self, "capability-scaffold-skill", outcome)

    def test_scaffold_agent(self):
        outcome = run_golden([
            "capability", "scaffold-agent", "demo-agent", "--description", "Demo agent.",
            "--capability-class", "fast-default", "--effort", "standard",
        ])
        assert_golden(self, "capability-scaffold-agent", outcome)

    def test_scaffold_skill_force_overwrites_existing(self):
        outcome = run_golden(
            ["capability", "scaffold-skill", "demo-skill", "--description", "Demo skill.", "--force"],
            extra_fixture={".hydra-framework/capabilities/skills/demo-skill/skill.md": "# Existing\n"},
        )
        assert_golden(self, "capability-scaffold-skill-force-overwrites", outcome)


if __name__ == "__main__":
    unittest.main()
