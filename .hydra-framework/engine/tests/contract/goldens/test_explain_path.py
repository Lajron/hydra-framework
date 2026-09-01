"""explain-path goldens."""

from __future__ import annotations

import unittest

from .fixtures import FROZEN_UID, assert_golden, run_golden

UNIT_PATH = ".hydra-framework/repo/knowledge-units/0001-fixture.md"
UNIT_OBJECT = (
    "---\n"
    "hydra_id: hydra://knowledge-unit/0001-fixture\n"
    f"uid: {FROZEN_UID}\n"
    "schema_version: 3\n"
    "kind: knowledge-unit\n"
    "title: Fixture Unit\n"
    "status: accepted\n"
    "scope: repo-local\n"
    "owners:\n"
    "  team: fixture-owners\n"
    "relations: []\n"
    "provenance:\n"
    "  sources:\n"
    "    - .hydra-framework/core/placement-rules.md\n"
    "---\n\n# Fixture Unit\n"
)


class ExplainPathGoldenTests(unittest.TestCase):
    def test_explain_path_object_happy_path(self):
        outcome = run_golden(["explain-path", UNIT_PATH], extra_fixture={UNIT_PATH: UNIT_OBJECT})
        assert_golden(self, "explain-path-object", outcome)

    def test_explain_path_provenance_citer_json(self):
        outcome = run_golden(
            ["explain-path", ".hydra-framework/core/placement-rules.md", "--json"],
            extra_fixture={UNIT_PATH: UNIT_OBJECT},
        )
        assert_golden(self, "explain-path-provenance-citer-json", outcome)

    def test_explain_path_authored_provider_file(self):
        outcome = run_golden(["explain-path", ".claude/settings.json"], extra_fixture={".claude/settings.json": "{}\n"})
        assert_golden(self, "explain-path-authored-provider", outcome)

    def test_explain_path_missing_path_json(self):
        outcome = run_golden(["explain-path", "nowhere/at/all.md", "--json"])
        assert_golden(self, "explain-path-missing", outcome)


if __name__ == "__main__":
    unittest.main()
