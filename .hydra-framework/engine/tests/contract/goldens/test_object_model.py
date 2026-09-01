"""Object-model goldens: ref resolve/check/index, move-object (happy path +
all seven refusal branches), schema upgrade.
"""

from __future__ import annotations

import unittest

from .fixtures import FROZEN_UID, assert_golden, hydra_object_markdown, run_golden

UNIT_PATH = ".hydra-framework/repo/knowledge-units/0001-fixture.md"
UNIT_OBJECT = hydra_object_markdown(hydra_id="hydra://knowledge-unit/0001-fixture", title="Fixture Unit")

BROKEN_REF_PATH = ".hydra-framework/repo/knowledge-units/0005-broken.md"
BROKEN_REF_OBJECT = (
    "---\n"
    "hydra_id: hydra://knowledge-unit/0005-broken\n"
    "uid: 11111111-1111-4111-8111-111111111111\n"
    "schema_version: 3\n"
    "kind: knowledge-unit\n"
    "title: Broken\n"
    "status: accepted\n"
    "scope: repo-local\n"
    "owners:\n"
    "  team: fixture-owners\n"
    "relations:\n"
    "  - hydra://knowledge-unit/does-not-exist\n"
    "provenance:\n"
    "  sources: []\n"
    "---\n\n# Broken\n"
)

ALIAS_A_PATH = ".hydra-framework/repo/knowledge-units/0003-a.md"
ALIAS_B_PATH = ".hydra-framework/repo/knowledge-units/0003-b.md"


def _alias_object(hydra_id: str, title: str) -> str:
    return (
        "---\n"
        f"hydra_id: {hydra_id}\n"
        f"uid: {FROZEN_UID}\n"
        "schema_version: 3\n"
        "kind: knowledge-unit\n"
        f"title: {title}\n"
        "status: accepted\n"
        "scope: repo-local\n"
        "aliases:\n"
        "  - hydra://knowledge-unit/shared-alias\n"
        "owners:\n"
        "  team: fixture-owners\n"
        "relations: []\n"
        "provenance:\n"
        "  sources: []\n"
        f"---\n\n# {title}\n"
    )


LEGACY_PATH = ".hydra-framework/repo/knowledge-units/legacy-unit.md"
LEGACY_OBJECT = "---\nhydra_id: hydra://knowledge-unit/legacy-unit\nstatus: accepted\n---\n\n# Legacy\n"


class RefGoldenTests(unittest.TestCase):
    def test_ref_resolve_happy_path(self):
        outcome = run_golden(
            ["ref", "resolve", "hydra://knowledge-unit/0001-fixture"],
            extra_fixture={UNIT_PATH: UNIT_OBJECT},
        )
        assert_golden(self, "object-ref-resolve", outcome)

    def test_ref_resolve_refusal_not_found(self):
        outcome = run_golden(["ref", "resolve", "hydra://knowledge-unit/does-not-exist"])
        assert_golden(self, "object-ref-resolve-refusal-not-found", outcome)

    def test_ref_resolve_refusal_ambiguous(self):
        outcome = run_golden(
            ["ref", "resolve", "hydra://knowledge-unit/shared-alias"],
            extra_fixture={
                ALIAS_A_PATH: _alias_object("hydra://knowledge-unit/0003-a", "Alias A"),
                ALIAS_B_PATH: _alias_object("hydra://knowledge-unit/0003-b", "Alias B"),
            },
        )
        assert_golden(self, "object-ref-resolve-refusal-ambiguous", outcome)

    def test_ref_check_happy_path(self):
        outcome = run_golden(["ref", "check"], extra_fixture={UNIT_PATH: UNIT_OBJECT})
        assert_golden(self, "object-ref-check", outcome)

    def test_ref_index_happy_path(self):
        outcome = run_golden(["ref", "index"], extra_fixture={UNIT_PATH: UNIT_OBJECT})
        assert_golden(self, "object-ref-index", outcome)


class SchemaUpgradeGoldenTests(unittest.TestCase):
    def test_schema_upgrade_happy_path(self):
        """Empty object set: still a real happy path (`0 of 0 upgraded`)."""
        outcome = run_golden(["schema", "upgrade"])
        assert_golden(self, "object-schema-upgrade", outcome)

    def test_schema_upgrade_real_upgrade(self):
        outcome = run_golden(["schema", "upgrade"], extra_fixture={LEGACY_PATH: LEGACY_OBJECT})
        assert_golden(self, "object-schema-upgrade-applies", outcome)


class MoveObjectGoldenTests(unittest.TestCase):
    def test_move_object_happy_path_dry_run(self):
        outcome = run_golden(
            [
                "move-object",
                UNIT_PATH,
                ".hydra-framework/repo/knowledge-units/0001-fixture-moved.md",
                "--dry-run",
            ],
            extra_fixture={UNIT_PATH: UNIT_OBJECT},
        )
        assert_golden(self, "object-move-object-happy", outcome)

    def test_refusal_source_not_a_file(self):
        outcome = run_golden(["move-object", "nope.md", "elsewhere.md", "--dry-run"])
        assert_golden(self, "object-move-object-refusal-not-a-file", outcome)

    def test_refusal_source_not_a_canonical_object(self):
        outcome = run_golden(
            ["move-object", "plain.md", "elsewhere.md", "--dry-run"],
            extra_fixture={"plain.md": "# Just a file\n"},
        )
        assert_golden(self, "object-move-object-refusal-not-canonical", outcome)

    def test_refusal_no_uid(self):
        no_uid_path = ".hydra-framework/repo/knowledge-units/0002-fixture.md"
        no_uid_object = hydra_object_markdown(
            hydra_id="hydra://knowledge-unit/0002-fixture", title="No Uid", uid="", schema_version=1
        )
        outcome = run_golden(
            ["move-object", no_uid_path, ".hydra-framework/repo/knowledge-units/0002-fixture-moved.md", "--dry-run"],
            extra_fixture={no_uid_path: no_uid_object},
        )
        assert_golden(self, "object-move-object-refusal-no-uid", outcome)

    def test_refusal_destination_already_exists(self):
        existing_path = ".hydra-framework/repo/knowledge-units/0001-fixture-exists.md"
        outcome = run_golden(
            ["move-object", UNIT_PATH, existing_path, "--dry-run"],
            extra_fixture={UNIT_PATH: UNIT_OBJECT, existing_path: "already here\n"},
        )
        assert_golden(self, "object-move-object-refusal-destination-exists", outcome)

    def test_refusal_destination_changes_state_tier(self):
        outcome = run_golden(
            [
                "move-object",
                UNIT_PATH,
                ".hydra-framework/tasks/personal/someone/0001-fixture.md",
                "--dry-run",
            ],
            extra_fixture={UNIT_PATH: UNIT_OBJECT},
        )
        assert_golden(self, "object-move-object-refusal-tier-change", outcome)

    def test_refusal_broken_references_precondition(self):
        """Covers a gap deferred earlier: this refusal and the
        destination-suffix mismatch."""
        outcome = run_golden(
            [
                "move-object",
                UNIT_PATH,
                ".hydra-framework/repo/knowledge-units/0001-fixture-moved.md",
                "--dry-run",
            ],
            extra_fixture={UNIT_PATH: UNIT_OBJECT, BROKEN_REF_PATH: BROKEN_REF_OBJECT},
        )
        assert_golden(self, "object-move-object-refusal-broken-references", outcome)

    def test_refusal_destination_suffix_mismatch(self):
        outcome = run_golden(
            [
                "move-object",
                UNIT_PATH,
                ".hydra-framework/repo/knowledge-units/0001-fixture-moved.txt",
                "--dry-run",
            ],
            extra_fixture={UNIT_PATH: UNIT_OBJECT},
        )
        assert_golden(self, "object-move-object-refusal-suffix-mismatch", outcome)


if __name__ == "__main__":
    unittest.main()
