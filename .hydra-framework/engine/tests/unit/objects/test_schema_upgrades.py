"""Mirror test for `hydra_engine.objects.schema_upgrades`.

`EnvelopeBackfillTests` ported from the pre-existing
`scripts/tests/test_hydra.py::EnvelopeMigrationTests` coverage of the
backfill-uid/backfill-empty-envelope-slots steps and the multi-object/
standalone-YAML shapes, which this file's own `EnvelopeMigrationTests` did
not yet exercise)."""

from __future__ import annotations

import re
import sys
import unittest
from pathlib import Path

_SRC = Path(__file__).resolve().parents[3] / "src"
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

from hydra_engine.identity.schema_versions import CURRENT_SCHEMA_VERSION, UNVERSIONED_SCHEMA_VERSION  # noqa: E402
from hydra_engine.objects import schema_upgrades  # noqa: E402

FRONTMATTER = "hydra_id: hydra://knowledge-unit/0001-test\n"


class EnvelopeMigrationTests(unittest.TestCase):
    def test_chains_from_unversioned_straight_to_current_in_one_call(self):
        text, applied = schema_upgrades.upgrade_envelope_text(FRONTMATTER, "hydra://knowledge-unit/0001-test", UNVERSIONED_SCHEMA_VERSION)
        self.assertEqual(len(applied), 3)
        self.assertIn(f"schema_version: {CURRENT_SCHEMA_VERSION}", text)
        self.assertIn("uid:", text)
        self.assertIn("relations: []", text)

    def test_is_idempotent_on_second_run(self):
        once, _ = schema_upgrades.upgrade_envelope_text(FRONTMATTER, "hydra://knowledge-unit/0001-test", UNVERSIONED_SCHEMA_VERSION)
        twice, applied_again = schema_upgrades.upgrade_envelope_text(once, "hydra://knowledge-unit/0001-test", CURRENT_SCHEMA_VERSION)
        self.assertEqual(once, twice)
        self.assertEqual(applied_again, [])

    def test_object_already_current_is_left_untouched(self):
        text, applied = schema_upgrades.upgrade_envelope_text(FRONTMATTER, "hydra://knowledge-unit/0001-test", CURRENT_SCHEMA_VERSION)
        self.assertEqual(text, FRONTMATTER)
        self.assertEqual(applied, [])

    def test_introduce_schema_version_adds_field_next_to_hydra_id(self):
        text, changed = schema_upgrades._introduce_schema_version(FRONTMATTER, "hydra://knowledge-unit/0001-test", 1)
        self.assertTrue(changed)
        self.assertEqual(text.splitlines()[1], "schema_version: 1")


class EnvelopeBackfillTests(unittest.TestCase):
    """Full frontmatter-object fixtures (unlike the module-level `FRONTMATTER`
    one-liner above): these exercise backfill-uid and
    backfill-empty-envelope-slots, which need real `owners`/`relations`/
    `provenance` shapes to backfill against."""

    RICH_FRONTMATTER = (
        "---\n"
        "hydra_id: hydra://knowledge-unit/0001-test\n"
        "kind: knowledge-unit\n"
        "title: Test Object\n"
        "status: active\n"
        "scope: base-seed\n"
        "owners:\n"
        "  team: hydra\n"
        "relations:\n"
        "provenance:\n"
        "  sources: []\n"
        "---\n"
        "# Test Object\n"
    )

    SIDECAR = (
        "schema: hydra-framework.object-sidecar.v1\n"
        "objects:\n"
        "  first-template:\n"
        "    hydra_id: hydra://knowledge-template/package/first\n"
        "    kind: knowledge-template\n"
        "    path: .hydra-framework/repo/knowledge/first.md\n"
        "  second-template:\n"
        "    hydra_id: hydra://knowledge-template/package/second\n"
        "    kind: knowledge-template\n"
        "    path: .hydra-framework/repo/knowledge/second.md\n"
    )

    STANDALONE_YAML = (
        "schema: hydra-framework.skill.v1\n"
        "hydra_id: hydra://capability/skill/example\n"
        "hydra_object_kind: skill\n"
        "name: example\n"
        "scope: common-seed\n"
    )

    # A v1 object: already has schema_version, still missing uid. Used to
    # exercise the backfill-uid step in isolation from introduce-schema-version.
    FRONTMATTER_V1 = RICH_FRONTMATTER.replace(
        "hydra_id: hydra://knowledge-unit/0001-test\n",
        "hydra_id: hydra://knowledge-unit/0001-test\nschema_version: 1\n",
    )

    # A v2 object: has schema_version and uid, but neither empty-able slot.
    # Used to exercise backfill-empty-envelope-slots in isolation.
    FRONTMATTER_V2 = (
        "---\n"
        "hydra_id: hydra://knowledge-unit/0001-test\n"
        "uid: 11111111-1111-4111-8111-111111111111\n"
        "schema_version: 2\n"
        "kind: knowledge-unit\n"
        "title: Test Object\n"
        "status: active\n"
        "scope: base-seed\n"
        "owners:\n"
        "  team: hydra\n"
        "---\n"
        "# Test Object\n"
    )

    UUID4_RE = re.compile(r"^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$")

    def test_adds_schema_version_at_root_of_standalone_yaml_object(self):
        text, changed = schema_upgrades._introduce_schema_version(self.STANDALONE_YAML, "hydra://capability/skill/example", 1)
        self.assertTrue(changed)
        lines = text.splitlines()
        anchor = lines.index("hydra_id: hydra://capability/skill/example")
        self.assertEqual(lines[anchor + 1], "schema_version: 1")

    def test_upgrades_only_the_named_object_in_a_multi_object_sidecar(self):
        text, applied = schema_upgrades.upgrade_envelope_text(
            self.SIDECAR, "hydra://knowledge-template/package/first", UNVERSIONED_SCHEMA_VERSION
        )
        self.assertEqual(applied, ["introduce-schema-version", "backfill-uid", "backfill-empty-envelope-slots"])
        lines = text.splitlines()
        first_anchor = lines.index("    hydra_id: hydra://knowledge-template/package/first")
        self.assertTrue(lines[first_anchor + 1].strip().startswith("uid:"))
        self.assertEqual(lines[first_anchor + 2], f"    schema_version: {CURRENT_SCHEMA_VERSION}")
        # The second object in the same file is untouched by this call.
        second_anchor = lines.index("    hydra_id: hydra://knowledge-template/package/second")
        self.assertEqual(lines[second_anchor + 1], "    kind: knowledge-template")

    def test_backfill_uid_adds_opaque_uid_and_bumps_schema_version(self):
        text, applied = schema_upgrades.upgrade_envelope_text(self.FRONTMATTER_V1, "hydra://knowledge-unit/0001-test", 1)
        self.assertEqual(applied, ["backfill-uid", "backfill-empty-envelope-slots"])
        lines = text.splitlines()
        self.assertEqual(lines[1], "hydra_id: hydra://knowledge-unit/0001-test")
        uid_line = lines[2]
        self.assertTrue(uid_line.startswith("uid: "))
        self.assertRegex(uid_line.removeprefix("uid: "), self.UUID4_RE)
        self.assertEqual(lines[3], f"schema_version: {CURRENT_SCHEMA_VERSION}")

    def test_backfill_uid_is_idempotent_and_preserves_assigned_uid(self):
        once, _ = schema_upgrades.upgrade_envelope_text(self.FRONTMATTER_V1, "hydra://knowledge-unit/0001-test", 1)
        twice, applied_again = schema_upgrades.upgrade_envelope_text(once, "hydra://knowledge-unit/0001-test", CURRENT_SCHEMA_VERSION)
        self.assertEqual(applied_again, [])
        self.assertEqual(once, twice)

    def test_uid_is_opaque_and_unique_per_object(self):
        first_text, _ = schema_upgrades.upgrade_envelope_text(self.FRONTMATTER_V1, "hydra://knowledge-unit/0001-test", 1)
        second_source = self.FRONTMATTER_V1.replace("0001-test", "0002-test")
        second_text, _ = schema_upgrades.upgrade_envelope_text(second_source, "hydra://knowledge-unit/0002-test", 1)

        def uid_of(text: str) -> str:
            return next(line for line in text.splitlines() if line.startswith("uid: ")).removeprefix("uid: ")

        first_uid, second_uid = uid_of(first_text), uid_of(second_text)
        self.assertRegex(first_uid, self.UUID4_RE)
        self.assertRegex(second_uid, self.UUID4_RE)
        self.assertNotEqual(first_uid, second_uid)
        self.assertNotIn("0001-test", first_uid)
        self.assertNotIn("0002-test", second_uid)

    def test_backfill_adds_both_empty_slots_and_bumps_schema_version(self):
        text, applied = schema_upgrades.upgrade_envelope_text(self.FRONTMATTER_V2, "hydra://knowledge-unit/0001-test", 2)
        self.assertEqual(applied, ["backfill-empty-envelope-slots"])
        lines = text.splitlines()
        self.assertEqual(lines[3], f"schema_version: {CURRENT_SCHEMA_VERSION}")
        # Appended at the end of the envelope block, before the frontmatter close.
        self.assertEqual(lines[-5:-1], ["relations: []", "provenance:", "  sources: []", "---"])
        self.assertTrue(text.endswith("# Test Object\n"))

    def test_backfill_writes_only_the_two_fields_an_empty_value_is_true_for(self):
        # kind, title, status, scope, and owners are absent here and stay
        # absent: there is no value for them that would be true without an
        # author, so the migration must not supply one.
        bare = (
            "---\n"
            "hydra_id: hydra://knowledge-unit/0001-test\n"
            "uid: 11111111-1111-4111-8111-111111111111\n"
            "schema_version: 2\n"
            "---\n"
        )
        text, applied = schema_upgrades.upgrade_envelope_text(bare, "hydra://knowledge-unit/0001-test", 2)
        self.assertEqual(applied, ["backfill-empty-envelope-slots"])
        for invented in ("kind:", "title:", "status:", "scope:", "owners:"):
            self.assertNotIn(invented, text)
        self.assertIn("relations: []", text)
        self.assertIn("provenance:\n  sources: []", text)

    def test_backfill_leaves_declared_relations_and_sources_untouched(self):
        declared = self.FRONTMATTER_V2.replace(
            "owners:\n  team: hydra\n",
            "owners:\n  team: hydra\n"
            "relations:\n  - hydra://knowledge-unit/0002-other\n"
            "provenance:\n  sources:\n    - repo/knowledge/note.md\n",
        )
        text, applied = schema_upgrades.upgrade_envelope_text(declared, "hydra://knowledge-unit/0001-test", 2)
        self.assertEqual(applied, ["backfill-empty-envelope-slots"])
        self.assertIn("  - hydra://knowledge-unit/0002-other", text)
        self.assertIn("    - repo/knowledge/note.md", text)
        self.assertNotIn("relations: []", text)
        self.assertNotIn("sources: []", text)
        self.assertEqual(text, declared.replace("schema_version: 2", f"schema_version: {CURRENT_SCHEMA_VERSION}"))

    def test_backfill_nests_sources_under_an_existing_provenance_block(self):
        with_provenance = self.FRONTMATTER_V2.replace(
            "owners:\n  team: hydra\n",
            "owners:\n  team: hydra\nprovenance:\n  reviewed_by: hydra\n",
        )
        text, _ = schema_upgrades.upgrade_envelope_text(with_provenance, "hydra://knowledge-unit/0001-test", 2)
        self.assertIn("provenance:\n  sources: []\n  reviewed_by: hydra", text)
        self.assertEqual(text.count("provenance:"), 1)

    def test_backfill_is_idempotent(self):
        once, _ = schema_upgrades.upgrade_envelope_text(self.FRONTMATTER_V2, "hydra://knowledge-unit/0001-test", 2)
        twice, applied_again = schema_upgrades.upgrade_envelope_text(once, "hydra://knowledge-unit/0001-test", CURRENT_SCHEMA_VERSION)
        self.assertEqual(applied_again, [])
        self.assertEqual(once, twice)

    def test_a_v1_object_that_already_carries_a_uid_still_advances(self):
        # A downstream copy that backfilled uid by hand is recorded below the
        # version its envelope already satisfies. It has to keep moving, or it
        # would sit below every later migration forever.
        hand_backfilled = self.FRONTMATTER_V1.replace(
            "hydra_id: hydra://knowledge-unit/0001-test\n",
            "hydra_id: hydra://knowledge-unit/0001-test\nuid: 11111111-1111-4111-8111-111111111111\n",
        )
        text, applied = schema_upgrades.upgrade_envelope_text(hand_backfilled, "hydra://knowledge-unit/0001-test", 1)
        self.assertEqual(applied, ["backfill-uid", "backfill-empty-envelope-slots"])
        self.assertIn(f"schema_version: {CURRENT_SCHEMA_VERSION}", text.splitlines())
        # The hand-assigned identity survives rather than being reissued.
        self.assertEqual(text.count("uid: 11111111-1111-4111-8111-111111111111"), 1)


if __name__ == "__main__":
    unittest.main()
