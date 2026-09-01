"""Mirror test for `hydra_engine.objects.references`."""

from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

_SRC = Path(__file__).resolve().parents[3] / "src"
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

from hydra_engine.identity.schema_versions import ENVELOPE_REQUIRED_FROM_SCHEMA_VERSION  # noqa: E402
from hydra_engine.objects import discovery, references  # noqa: E402


def _paths(root: Path) -> discovery.ObjectLocations:
    hydra = root / ".hydra-framework"
    return discovery.ObjectLocations(
        root=root,
        hydra=hydra,
        local=root / ".hydra-framework.local",
        personal_tasks_rel="tasks/personal",
        object_registry=hydra / "cognition/graph/registry.yaml",
    )


def _object(root: Path, name: str, hydra_id: str, *, extra: str = "") -> None:
    hydra = root / ".hydra-framework"
    (hydra / name).parent.mkdir(parents=True, exist_ok=True)
    (hydra / name).write_text(
        f"---\nhydra_id: {hydra_id}\nstatus: active\nscope: repo\nowners:\n  a: '2026-08-17'\n"
        f"relations: []\nprovenance:\n  sources: []\n---\n# Title\n\n{extra}\n",
        encoding="utf-8",
    )


def _seed(root: Path, rel: str, content: str) -> Path:
    path = root / ".hydra-framework" / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    return path


ENVELOPE_BLOCKS = {
    "kind": "kind: source\n",
    "title": "title: Test Object\n",
    "status": "status: active\n",
    "scope": "scope: base-seed\n",
    "owners": "owners:\n  team: hydra\n",
    "relations": "relations: []\n",
    "provenance.sources": "provenance:\n  sources: []\n",
}


def _envelope_object(root: Path, *, omit: str = "", heading: str = "# Test Object\n") -> Path:
    """A complete envelope at the version that requires one, minus `omit`."""
    body = "".join(text for field, text in ENVELOPE_BLOCKS.items() if field != omit)
    return _seed(
        root,
        "source/0001-a.md",
        "---\n"
        "hydra_id: hydra://source/0001-a\n"
        "uid: 11111111-1111-4111-8111-111111111111\n"
        f"schema_version: {ENVELOPE_REQUIRED_FROM_SCHEMA_VERSION}\n"
        f"{body}"
        "---\n" + heading,
    )


def _provenance_object(root: Path, source: str) -> None:
    _seed(
        root,
        "source/0001-a.md",
        "---\n"
        "hydra_id: hydra://source/0001-a\n"
        "uid: 11111111-1111-4111-8111-111111111111\n"
        f"schema_version: {ENVELOPE_REQUIRED_FROM_SCHEMA_VERSION}\n"
        "kind: source\n"
        "title: Test Object\n"
        "status: active\n"
        "scope: base-seed\n"
        "owners:\n  team: hydra\n"
        "relations: []\n"
        f"provenance:\n  sources:\n    - {source}\n"
        "---\n# Test Object\n",
    )


class ValidateObjectReferencesTests(unittest.TestCase):
    def test_no_objects_is_clean(self):
        root = Path(tempfile.mkdtemp(prefix="references-test-"))
        (root / ".hydra-framework").mkdir()
        self.assertEqual(references.validate_object_references(_paths(root)), [])

    def test_duplicate_ids_are_validation_errors(self):
        root = Path(tempfile.mkdtemp(prefix="references-test-"))
        _object(root, "a.md", "hydra://source/0001-test")
        _object(root, "b.md", "hydra://source/0001-test")
        errors = references.validate_object_references(_paths(root))
        self.assertTrue(any("duplicate hydra_id" in error for error in errors))

    def test_unresolved_reference_is_reported(self):
        root = Path(tempfile.mkdtemp(prefix="references-test-"))
        _object(root, "a.md", "hydra://source/0001-test", extra="See hydra://source/9999-missing.")
        errors = references.validate_object_references(_paths(root))
        self.assertTrue(any("references unresolved" in error for error in errors))

    def test_missing_provenance_source_path_is_reported(self):
        root = Path(tempfile.mkdtemp(prefix="references-test-"))
        (root / "docs").mkdir()
        _provenance_object(root, "docs/missing.md")
        findings = references.validate_object_references(_paths(root))
        self.assertTrue(any("`provenance.sources` path does not exist: docs/missing.md" in str(e) for e in findings))

    def test_existing_provenance_source_path_is_clean(self):
        root = Path(tempfile.mkdtemp(prefix="references-test-"))
        (root / "docs").mkdir()
        (root / "docs/source.md").write_text("source\n", encoding="utf-8")
        _provenance_object(root, "docs/source.md")
        self.assertEqual(references.validate_object_references(_paths(root)), [])

    def test_non_path_provenance_source_is_ignored(self):
        root = Path(tempfile.mkdtemp(prefix="references-test-"))
        _provenance_object(root, "https://example.invalid/source")
        self.assertEqual(references.validate_object_references(_paths(root)), [])

    def test_sidecar_provenance_source_resolves_against_the_sidecar(self):
        root = Path(tempfile.mkdtemp(prefix="references-test-"))
        _seed(root, "knowledge/notes.txt", "Not a Markdown object.\n")
        _seed(root, "source.md", "source\n")
        _seed(
            root,
            "object-sidecars.yaml",
            "schema: hydra-framework.object-sidecar.v1\n"
            "objects:\n"
            "  notes:\n"
            "    hydra_id: hydra://source/notes\n"
            "    uid: 11111111-1111-4111-8111-111111111111\n"
            f"    schema_version: {ENVELOPE_REQUIRED_FROM_SCHEMA_VERSION}\n"
            "    kind: source\n"
            "    title: Notes\n"
            "    status: active\n"
            "    scope: base-seed\n"
            "    owners:\n"
            "      team: hydra\n"
            "    relations: []\n"
            "    path: knowledge/notes.txt\n"
            "    provenance:\n"
            "      sources:\n"
            "        - ./source.md\n",
        )
        self.assertEqual(references.validate_object_references(_paths(root)), [])

    def test_missing_uid_finding_carries_the_objects_own_path(self):
        root = Path(tempfile.mkdtemp(prefix="references-test-"))
        (root / ".hydra-framework").mkdir(parents=True, exist_ok=True)
        (root / ".hydra-framework/a.md").write_text(
            "---\nhydra_id: hydra://source/0001-test\nschema_version: 2\nstatus: active\nscope: repo\n"
            "owners:\n  a: '2026-08-17'\nrelations: []\nprovenance:\n  sources: []\n---\n# Title\n",
            encoding="utf-8",
        )
        findings = references.validate_object_references(_paths(root))
        missing_uid = [f for f in findings if f.code == "object-references" and "missing required uid" in f.detail]
        self.assertEqual(len(missing_uid), 1)
        self.assertEqual(missing_uid[0].path, ".hydra-framework/a.md")

    def test_duplicate_id_finding_has_no_single_path(self):
        root = Path(tempfile.mkdtemp(prefix="references-test-"))
        _object(root, "a.md", "hydra://source/0001-test")
        _object(root, "b.md", "hydra://source/0001-test")
        findings = references.validate_object_references(_paths(root))
        duplicates = [f for f in findings if "duplicate hydra_id" in f.detail]
        self.assertEqual(len(duplicates), 1)
        self.assertEqual(duplicates[0].path, "")

    def test_duplicate_uids_are_validation_errors(self):
        # Moved from `test_hydra.py`'s `ObjectReferenceTests`: two distinct
        # hydra_ids sharing one uid.
        root = Path(tempfile.mkdtemp(prefix="references-test-"))
        _seed(
            root, "source/0001-a.md",
            "---\nhydra_id: hydra://source/0001-a\n"
            "uid: 11111111-1111-4111-8111-111111111111\n"
            "kind: source\ntitle: Test Object\nstatus: active\nscope: base-seed\n"
            "relations:\nprovenance:\n  sources: []\n---\n# Test Object\n",
        )
        _seed(
            root, "source/0002-b.md",
            "---\nhydra_id: hydra://source/0002-b\n"
            "uid: 11111111-1111-4111-8111-111111111111\n"
            "kind: source\ntitle: Test Object\nstatus: active\nscope: base-seed\n"
            "relations:\nprovenance:\n  sources: []\n---\n# Test Object\n",
        )
        errors = references.validate_object_references(_paths(root))
        self.assertTrue(any("duplicate uid `11111111-1111-4111-8111-111111111111`" in str(e) for e in errors))


class EnvelopeRequiredFieldsTests(unittest.TestCase):
    """The mandatory envelope, gated on
    `ENVELOPE_REQUIRED_FROM_SCHEMA_VERSION` -- moved from `test_hydra.py`'s
    `ObjectReferenceTests`."""

    def only_object(self, root: Path) -> dict:
        objects, errors = discovery.collect_hydra_objects(_paths(root))
        self.assertEqual(errors, [])
        return objects[0]

    def test_complete_envelope_at_required_schema_version_is_clean(self):
        root = Path(tempfile.mkdtemp(prefix="references-test-"))
        _envelope_object(root)
        self.assertEqual(references.validate_object_references(_paths(root)), [])

    def test_incomplete_envelope_below_required_schema_version_is_not_an_error(self):
        # No schema_version line at all (version 0) predates the mandatory envelope.
        root = Path(tempfile.mkdtemp(prefix="references-test-"))
        _object(root, "a.md", "hydra://source/0001-a")
        self.assertEqual(references.validate_object_references(_paths(root)), [])

    def test_missing_owners_at_required_schema_version_is_a_validation_error(self):
        root = Path(tempfile.mkdtemp(prefix="references-test-"))
        _envelope_object(root, omit="owners")
        errors = references.validate_object_references(_paths(root))
        self.assertIn("source/0001-a.md is missing required owners", "\n".join(str(e) for e in errors))

    def test_absent_relations_is_an_error_that_names_the_empty_list_as_the_answer(self):
        root = Path(tempfile.mkdtemp(prefix="references-test-"))
        _envelope_object(root, omit="relations")
        errors = references.validate_object_references(_paths(root))
        relations_errors = [e for e in errors if "missing required relations" in str(e)]
        self.assertEqual(len(relations_errors), 1)
        self.assertIn("an empty list is the right answer", str(relations_errors[0]))

    def test_absent_provenance_sources_is_a_validation_error(self):
        root = Path(tempfile.mkdtemp(prefix="references-test-"))
        _envelope_object(root, omit="provenance.sources")
        errors = references.validate_object_references(_paths(root))
        sources_errors = [e for e in errors if "missing required provenance.sources" in str(e)]
        self.assertEqual(len(sources_errors), 1)
        self.assertIn("an empty list is the right answer", str(sources_errors[0]))

    def test_empty_relations_and_sources_pass_while_absent_ones_fail(self):
        root = Path(tempfile.mkdtemp(prefix="references-test-"))
        _envelope_object(root)
        obj = self.only_object(root)
        self.assertEqual(obj["relations"], [])
        self.assertEqual(obj["provenance_sources"], [])
        self.assertEqual(obj["missing_envelope_fields"], [])
        self.assertEqual(references.validate_object_references(_paths(root)), [])

    def test_absent_status_is_no_longer_defaulted_to_active(self):
        root = Path(tempfile.mkdtemp(prefix="references-test-"))
        _envelope_object(root, omit="status")
        self.assertEqual(self.only_object(root)["status"], "")
        errors = references.validate_object_references(_paths(root))
        self.assertIn("source/0001-a.md is missing required status", "\n".join(str(e) for e in errors))

    def test_absent_scope_is_no_longer_defaulted_to_unspecified(self):
        root = Path(tempfile.mkdtemp(prefix="references-test-"))
        _envelope_object(root, omit="scope")
        self.assertEqual(self.only_object(root)["scope"], "")
        errors = references.validate_object_references(_paths(root))
        self.assertIn("source/0001-a.md is missing required scope", "\n".join(str(e) for e in errors))

    def test_absent_kind_is_no_longer_derived_from_the_hydra_id(self):
        root = Path(tempfile.mkdtemp(prefix="references-test-"))
        _envelope_object(root, omit="kind")
        obj = self.only_object(root)
        self.assertEqual(obj["kind"], "")
        # The family still resolves from the hydra_id prefix; only the kind
        # field itself stopped being read back out of the ID.
        self.assertEqual(obj["family"], "Source")
        errors = references.validate_object_references(_paths(root))
        self.assertIn("source/0001-a.md is missing required kind", "\n".join(str(e) for e in errors))

    def test_status_may_be_spelled_maturity(self):
        # Reading a second spelling a human actually wrote is not defaulting.
        root = Path(tempfile.mkdtemp(prefix="references-test-"))
        _seed(
            root,
            "capabilities/skills/example/metadata.yaml",
            "schema: hydra-framework.skill.v2\n"
            "hydra_id: hydra://capability/skill/example\n"
            "uid: 11111111-1111-4111-8111-111111111111\n"
            f"schema_version: {ENVELOPE_REQUIRED_FROM_SCHEMA_VERSION}\n"
            "hydra_object_kind: skill\n"
            "name: example\n"
            "scope: common-seed\n"
            "maturity: seed\n"
            "owners:\n"
            "  team: hydra\n"
            "relations: []\n"
            "provenance:\n"
            "  sources: []\n",
        )
        obj = self.only_object(root)
        self.assertEqual(obj["status"], "seed")
        self.assertEqual(obj["kind"], "skill")
        self.assertEqual(obj["title"], "example")
        self.assertEqual(references.validate_object_references(_paths(root)), [])

    def test_title_falls_back_to_the_objects_own_heading_but_not_past_it(self):
        root = Path(tempfile.mkdtemp(prefix="references-test-"))
        _envelope_object(root, omit="title")
        self.assertEqual(self.only_object(root)["title"], "Test Object")
        self.assertEqual(references.validate_object_references(_paths(root)), [])

        root2 = Path(tempfile.mkdtemp(prefix="references-test-"))
        _envelope_object(root2, omit="title", heading="Body with no heading.\n")
        self.assertEqual(self.only_object(root2)["title"], "")
        errors = references.validate_object_references(_paths(root2))
        self.assertIn("source/0001-a.md is missing required title", "\n".join(str(e) for e in errors))

    def test_sidecar_entry_is_never_handed_its_own_filename_as_a_title(self):
        root = Path(tempfile.mkdtemp(prefix="references-test-"))
        _seed(root, "knowledge/notes.txt", "Not a Markdown object.\n")
        _seed(
            root,
            "object-sidecars.yaml",
            "schema: hydra-framework.object-sidecar.v1\n"
            "objects:\n"
            "  notes:\n"
            "    hydra_id: hydra://source/notes\n"
            "    uid: 11111111-1111-4111-8111-111111111111\n"
            f"    schema_version: {ENVELOPE_REQUIRED_FROM_SCHEMA_VERSION}\n"
            "    kind: source\n"
            "    status: active\n"
            "    scope: base-seed\n"
            "    owners:\n"
            "      team: hydra\n"
            "    relations: []\n"
            "    path: knowledge/notes.txt\n"
            "    provenance:\n"
            "      sources: []\n",
        )
        self.assertEqual(self.only_object(root)["title"], "")
        errors = references.validate_object_references(_paths(root))
        self.assertIn("knowledge/notes.txt is missing required title", "\n".join(str(e) for e in errors))


class DiscoveryAndReferenceEdgeCaseTests(unittest.TestCase):
    """Non-envelope discovery/reference edge cases -- moved from
    `test_hydra.py`'s `ObjectReferenceTests`."""

    def test_collects_yaml_object_outside_module_metadata(self):
        root = Path(tempfile.mkdtemp(prefix="references-test-"))
        _seed(
            root,
            "knowledge/knowledge-packages/hydra-framework/routing.yaml",
            "schema: hydra-framework.package-routing.v1\n"
            "hydra_id: hydra://knowledge-slice/hydra-framework/routing\n"
            "kind: knowledge-routing\n"
            "title: Hydra Framework Routing\n"
            "status: active\n"
            "scope: base-seed\n"
            "relations:\n"
            "  - hydra://knowledge-package/hydra-framework\n"
            "provenance:\n"
            "  sources: []\n",
        )
        _object(root, "knowledge/knowledge-packages/hydra-framework/overview.md", "hydra://knowledge-package/hydra-framework")
        objects, errors = discovery.collect_hydra_objects(_paths(root))
        self.assertEqual(errors, [])
        self.assertEqual(sorted(obj["id"] for obj in objects), [
            "hydra://knowledge-package/hydra-framework",
            "hydra://knowledge-slice/hydra-framework/routing",
        ])

    def test_collects_sidecar_object_for_file_without_inline_envelope(self):
        root = Path(tempfile.mkdtemp(prefix="references-test-"))
        _seed(root, "knowledge/knowledge-packages/templates/overview.md", "# <Package Name>\n")
        _seed(
            root,
            "object-sidecars.yaml",
            "schema: hydra-framework.object-sidecar.v1\n"
            "objects:\n"
            "  overview-template:\n"
            "    hydra_id: hydra://knowledge-template/package/overview\n"
            "    kind: knowledge-template\n"
            "    title: Package Overview Template\n"
            "    status: active\n"
            "    scope: base-seed\n"
            "    path: .hydra-framework/knowledge/knowledge-packages/templates/overview.md\n"
            "    provenance:\n"
            "      sources: []\n",
        )
        objects, errors = discovery.collect_hydra_objects(_paths(root))
        self.assertEqual(errors, [])
        self.assertEqual(len(objects), 1)
        self.assertEqual(objects[0]["id"], "hydra://knowledge-template/package/overview")
        self.assertEqual(objects[0]["envelope_path"], ".hydra-framework/object-sidecars.yaml")

    def test_sidecar_aliases_resolve_and_satisfy_references(self):
        root = Path(tempfile.mkdtemp(prefix="references-test-"))
        _seed(root, "knowledge/knowledge-packages/templates/overview.md", "# <Package Name>\n")
        _seed(
            root,
            "object-sidecars.yaml",
            "schema: hydra-framework.object-sidecar.v1\n"
            "objects:\n"
            "  overview-template:\n"
            "    hydra_id: hydra://knowledge-template/package/overview\n"
            "    aliases:\n"
            "      - hydra://knowledge-template/package/readme\n"
            "    kind: knowledge-template\n"
            "    title: Package Overview Template\n"
            "    status: active\n"
            "    scope: base-seed\n"
            "    path: .hydra-framework/knowledge/knowledge-packages/templates/overview.md\n"
            "    relations:\n"
            "      - hydra://knowledge-template/package/readme\n"
            "    provenance:\n"
            "      sources: []\n",
        )
        self.assertEqual(references.validate_object_references(_paths(root)), [])

    def test_sidecar_missing_target_is_validation_error(self):
        root = Path(tempfile.mkdtemp(prefix="references-test-"))
        _seed(
            root,
            "object-sidecars.yaml",
            "schema: hydra-framework.object-sidecar.v1\n"
            "objects:\n"
            "  missing-template:\n"
            "    hydra_id: hydra://knowledge-template/package/missing\n"
            "    kind: knowledge-template\n"
            "    path: .hydra-framework/knowledge/knowledge-packages/templates/missing.md\n",
        )
        errors = references.validate_object_references(_paths(root))
        self.assertTrue(any("points at missing path" in str(e) for e in errors))

    def test_alias_conflicts_are_validation_errors(self):
        root = Path(tempfile.mkdtemp(prefix="references-test-"))
        _object(root, "source/0001-a.md", "hydra://source/0001-a")
        _seed(root, "knowledge/knowledge-packages/templates/overview.md", "# <Package Name>\n")
        _seed(
            root,
            "object-sidecars.yaml",
            "schema: hydra-framework.object-sidecar.v1\n"
            "objects:\n"
            "  overview-template:\n"
            "    hydra_id: hydra://knowledge-template/package/overview\n"
            "    aliases:\n"
            "      - hydra://source/0001-a\n"
            "    kind: knowledge-template\n"
            "    title: Package Overview Template\n"
            "    status: active\n"
            "    scope: base-seed\n"
            "    path: .hydra-framework/knowledge/knowledge-packages/templates/overview.md\n",
        )
        errors = references.validate_object_references(_paths(root))
        self.assertTrue(any("duplicate hydra reference `hydra://source/0001-a`" in str(e) for e in errors))

    def test_missing_uid_below_required_schema_version_is_not_an_error(self):
        root = Path(tempfile.mkdtemp(prefix="references-test-"))
        _object(root, "source/0001-a.md", "hydra://source/0001-a")
        errors = references.validate_object_references(_paths(root))
        self.assertFalse(any("missing required uid" in str(e) for e in errors))

    def test_missing_uid_at_required_schema_version_is_a_validation_error(self):
        root = Path(tempfile.mkdtemp(prefix="references-test-"))
        _seed(
            root, "source/0001-a.md",
            "---\nhydra_id: hydra://source/0001-a\nschema_version: 2\nkind: source\n"
            "title: Test Object\nstatus: active\nscope: base-seed\nrelations:\n"
            "provenance:\n  sources: []\n---\n# Test Object\n",
        )
        errors = [str(e) for e in references.validate_object_references(_paths(root))]
        self.assertTrue(any("source/0001-a.md is missing required uid" in e for e in errors), errors)

    def test_uid_present_at_required_schema_version_is_not_an_error(self):
        root = Path(tempfile.mkdtemp(prefix="references-test-"))
        _seed(
            root, "source/0001-a.md",
            "---\nhydra_id: hydra://source/0001-a\nuid: 11111111-1111-4111-8111-111111111111\n"
            "schema_version: 2\nkind: source\ntitle: Test Object\nstatus: active\nscope: base-seed\n"
            "relations:\nprovenance:\n  sources: []\n---\n# Test Object\n",
        )
        errors = [str(e) for e in references.validate_object_references(_paths(root))]
        self.assertFalse(any("missing required uid" in e for e in errors), errors)

    def test_missing_uid_is_not_a_duplicate_violation(self):
        root = Path(tempfile.mkdtemp(prefix="references-test-"))
        _object(root, "source/0001-a.md", "hydra://source/0001-a")
        _object(root, "source/0002-b.md", "hydra://source/0002-b")
        errors = references.validate_object_references(_paths(root))
        self.assertFalse(any("duplicate uid" in str(e) for e in errors))

    def test_unresolved_hydra_refs_are_validation_errors(self):
        root = Path(tempfile.mkdtemp(prefix="references-test-"))
        _object(root, "source/0001-a.md", "hydra://source/0001-a", extra="See hydra://source/missing.")
        errors = references.validate_object_references(_paths(root))
        self.assertTrue(any("references unresolved `hydra://source/missing`" in str(e) for e in errors))

    def test_code_fence_examples_do_not_count_as_references(self):
        root = Path(tempfile.mkdtemp(prefix="references-test-"))
        _seed(root, "source/example.md", "```text\nhydra://source/example-only\n```\n")
        self.assertEqual(references.validate_object_references(_paths(root)), [])


def _family_object(root: Path, *, hydra_id: str, kind: str, schema_version: int) -> None:
    """A complete envelope whose id prefix and `kind` are the variables."""
    _seed(
        root,
        "source/0001-a.md",
        "---\n"
        f"hydra_id: {hydra_id}\n"
        "uid: 11111111-1111-4111-8111-111111111111\n"
        f"schema_version: {schema_version}\n"
        f"kind: {kind}\n"
        "title: Test Object\n"
        "status: active\n"
        "scope: base-seed\n"
        "owners:\n  team: hydra\n"
        "relations: []\n"
        "provenance:\n  sources: []\n"
        "---\n# Test Object\n",
    )


class UnregisteredObjectFamilyTests(unittest.TestCase):
    """The object-family registry, enforced. Before it, every one
    of these passed silently and exported `family: Unknown`."""

    def _errors(self, root: Path) -> str:
        return "\n".join(str(e) for e in references.validate_object_references(_paths(root)))

    def test_unregistered_id_prefix_is_reported(self):
        root = Path(tempfile.mkdtemp(prefix="references-test-"))
        _family_object(
            root, hydra_id="hydra://runtime-module/cli-dispatch", kind="source",
            schema_version=ENVELOPE_REQUIRED_FROM_SCHEMA_VERSION,
        )
        self.assertIn("has unregistered hydra_id family prefix `runtime-module`", self._errors(root))

    def test_unregistered_kind_is_reported(self):
        root = Path(tempfile.mkdtemp(prefix="references-test-"))
        _family_object(
            root, hydra_id="hydra://source/0001-a", kind="decisoin",
            schema_version=ENVELOPE_REQUIRED_FROM_SCHEMA_VERSION,
        )
        self.assertIn("has unregistered kind `decisoin`", self._errors(root))

    def test_the_finding_names_the_registry_to_edit(self):
        root = Path(tempfile.mkdtemp(prefix="references-test-"))
        _family_object(
            root, hydra_id="hydra://source/0001-a", kind="decisoin",
            schema_version=ENVELOPE_REQUIRED_FROM_SCHEMA_VERSION,
        )
        self.assertIn("hydra_engine.identity.object_families", self._errors(root))

    def test_a_registered_family_is_clean(self):
        root = Path(tempfile.mkdtemp(prefix="references-test-"))
        _family_object(
            root, hydra_id="hydra://capability/skill/example", kind="skill",
            schema_version=ENVELOPE_REQUIRED_FROM_SCHEMA_VERSION,
        )
        self.assertEqual(references.validate_object_references(_paths(root)), [])

    def test_an_object_below_the_envelope_version_is_not_judged(self):
        # `kind` is not a required field before this version, so the registry
        # has no standing to judge its value. A downstream copy that has not
        # run `schema upgrade` must not fail for someone else's lag.
        root = Path(tempfile.mkdtemp(prefix="references-test-"))
        _family_object(
            root, hydra_id="hydra://mystery/x", kind="mystery",
            schema_version=ENVELOPE_REQUIRED_FROM_SCHEMA_VERSION - 1,
        )
        self.assertNotIn("unregistered", self._errors(root))


if __name__ == "__main__":
    unittest.main()
