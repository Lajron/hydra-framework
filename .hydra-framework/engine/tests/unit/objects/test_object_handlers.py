"""Mirror test for `hydra_engine.objects.object_handlers` (the
second extension registry).

Four jobs: prove the suffix switch's behavior survived becoming data, prove
the registry is internally consistent, prove the new Python form is scoped the
way its docstring claims, and prove a Python envelope stays compatible with
the line-based field surgery `schema upgrade` and `move-object` depend on.
"""

from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

_SRC = Path(__file__).resolve().parents[3] / "src"
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

from hydra_engine.documents.tokens import HydraYamlError  # noqa: E402
from hydra_engine.objects import envelopes, object_handlers  # noqa: E402

_ENVELOPE = (
    '"""---\n'
    "hydra_id: hydra://engine-module/example\n"
    "uid: 00000000-0000-4000-8000-000000000000\n"
    "schema_version: 3\n"
    "kind: engine-module\n"
    "title: Example Engine Module\n"
    "---\n"
    "\n"
    'Prose about the module.\n"""\n'
)


def _hydra_tree() -> Path:
    hydra = Path(tempfile.mkdtemp(prefix="handlers-test-")) / ".hydra-framework"
    hydra.mkdir(parents=True)
    return hydra


def _write(path: Path, text: str) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return path


class RegistryConsistencyTests(unittest.TestCase):
    def test_no_suffix_is_claimed_by_two_handlers(self):
        # The invariant that makes `handler_for`'s answer independent of tuple
        # order. Enforced as a test, not at runtime, for the same reason the
        # object-family registry's equivalent invariant is: the registry is
        # code, so the point of edit is where this is reviewable.
        claimed: dict[str, str] = {}
        for handler in object_handlers.OBJECT_HANDLERS:
            for suffix in handler.suffixes:
                self.assertNotIn(
                    suffix, claimed,
                    f"suffix `{suffix}` claimed by both {claimed.get(suffix)} and {handler.name}",
                )
                claimed[suffix] = handler.name

    def test_every_handler_claims_a_suffix_and_can_name_a_kind(self):
        for handler in object_handlers.OBJECT_HANDLERS:
            self.assertTrue(handler.suffixes, f"{handler.name} claims no suffix")
            self.assertTrue(handler.kind_keys, f"{handler.name} declares no kind spelling")

    def test_handler_for_claims_the_three_forms_and_nothing_else(self):
        self.assertEqual(object_handlers.handler_for(Path("a.md")).name, "Markdown")
        self.assertEqual(object_handlers.handler_for(Path("a.yaml")).name, "YAML")
        self.assertEqual(object_handlers.handler_for(Path("a.yml")).name, "YAML")
        self.assertEqual(object_handlers.handler_for(Path("a.py")).name, "Python")
        # None is a real answer: a sidecar may name a `.txt` or `.sh` object,
        # and such a file has no envelope of its own to read.
        self.assertIsNone(object_handlers.handler_for(Path("a.txt")))
        self.assertIsNone(object_handlers.handler_for(Path("a.sh")))


class PathCollectionParityTests(unittest.TestCase):
    """The exclusions the suffix switch inlined, now handler data."""

    def test_markdown_and_yaml_are_collected(self):
        hydra = _hydra_tree()
        _write(hydra / "repo/knowledge-units/0001.md", "---\n---\n")
        _write(hydra / "repo/routing.yaml", "title: Routing\n")
        _write(hydra / "repo/routing.yml", "title: Routing\n")
        found = {p.name for p in object_handlers.object_document_paths(hydra)}
        self.assertEqual(found, {"0001.md", "routing.yaml", "routing.yml"})

    def test_yaml_skips_the_derived_cognition_root_but_markdown_does_not(self):
        # Exactly the previous asymmetry: the YAML branch excluded
        # `paths.hydra / "cognition"`; the Markdown branch never did.
        hydra = _hydra_tree()
        _write(hydra / "cognition/graph/registry.yaml", "schema: x\n")
        _write(hydra / "cognition/notes.md", "# Notes\n")
        found = {p.name for p in object_handlers.object_document_paths(hydra)}
        self.assertEqual(found, {"notes.md"})

    def test_markdown_skips_a_component_named_anywhere_in_the_path(self):
        # The Markdown branch's rule was any path *component*, not a root.
        hydra = _hydra_tree()
        _write(hydra / "repo/node_modules/pkg/readme.md", "# Vendored\n")
        _write(hydra / "repo/dist/out.md", "# Built\n")
        _write(hydra / "repo/real.md", "# Real\n")
        found = {p.name for p in object_handlers.object_document_paths(hydra)}
        self.assertEqual(found, {"real.md"})


class PythonScopeTests(unittest.TestCase):
    def test_python_is_collected_only_under_the_engine_source_root(self):
        hydra = _hydra_tree()
        _write(hydra / "engine/src/hydra_engine/thing.py", '"""Prose."""\n')
        # Both deliberately out of scope: `scripts/hydra.py` is a
        # compatibility surface rather than architecture, and
        # test fixtures author example `hydra://` ids that are not objects.
        _write(hydra / "scripts/hydra.py", '"""Shim."""\n')
        _write(hydra / "engine/tests/unit/test_thing.py", '"""Test."""\n')
        found = {
            p.relative_to(hydra).as_posix()
            for p in object_handlers.object_document_paths(hydra)
            if p.suffix == ".py"
        }
        self.assertEqual(found, {"engine/src/hydra_engine/thing.py"})

    def test_bytecode_directories_are_skipped(self):
        hydra = _hydra_tree()
        _write(hydra / "engine/src/hydra_engine/__pycache__/thing.py", '"""Cached."""\n')
        self.assertEqual(
            [p for p in object_handlers.object_document_paths(hydra) if p.suffix == ".py"], []
        )


class ReadObjectEnvelopeTests(unittest.TestCase):
    def test_markdown_falls_back_to_its_own_heading_for_a_title(self):
        hydra = _hydra_tree()
        path = _write(hydra / "doc.md", "---\nkind: knowledge-unit\n---\n\n# Written By A Human\n")
        data, title, kind = object_handlers.read_object_envelope(path, hydra)
        self.assertEqual(title, "Written By A Human")
        self.assertEqual(kind, "knowledge-unit")
        self.assertEqual(data["kind"], "knowledge-unit")

    def test_yaml_reads_the_alternate_authored_spellings(self):
        hydra = _hydra_tree()
        path = _write(hydra / "manifest.yaml", "name: Tool Registry\nhydra_object_kind: tool-capability-registry\n")
        _data, title, kind = object_handlers.read_object_envelope(path, hydra)
        self.assertEqual(title, "Tool Registry")
        self.assertEqual(kind, "tool-capability-registry")

    def test_declared_title_wins_over_the_alternate_spelling(self):
        hydra = _hydra_tree()
        path = _write(hydra / "manifest.yaml", "title: Declared\nname: Alternate\n")
        _data, title, _kind = object_handlers.read_object_envelope(path, hydra)
        self.assertEqual(title, "Declared")

    def test_python_reads_the_docstring_envelope(self):
        hydra = _hydra_tree()
        path = _write(hydra / "engine/src/hydra_engine/thing.py", _ENVELOPE)
        data, title, kind = object_handlers.read_object_envelope(path, hydra)
        self.assertEqual(data["hydra_id"], "hydra://engine-module/example")
        self.assertEqual(title, "Example Engine Module")
        self.assertEqual(kind, "engine-module")

    def test_a_python_module_without_an_envelope_declares_nothing(self):
        hydra = _hydra_tree()
        path = _write(hydra / "engine/src/hydra_engine/thing.py", '"""Ordinary prose."""\n\nX = 1\n')
        data, title, kind = object_handlers.read_object_envelope(path, hydra)
        self.assertEqual((data, title, kind), ({}, "", ""))

    def test_an_unclaimed_form_is_not_an_error(self):
        hydra = _hydra_tree()
        path = _write(hydra / "target.txt", "payload\n")
        self.assertIsNone(object_handlers.read_object_envelope(path, hydra))

    def test_a_claimed_but_unparseable_file_raises(self):
        # Distinct from the None above: the form is registered, so failing to
        # read it is a discovery error rather than "not an object".
        hydra = _hydra_tree()
        path = _write(hydra / "engine/src/hydra_engine/thing.py", "def broken(:\n")
        with self.assertRaises(HydraYamlError):
            object_handlers.read_object_envelope(path, hydra)


class PythonEnvelopeSurgeryTests(unittest.TestCase):
    """Why the envelope is docstring frontmatter and not a Python literal.

    `schema upgrade` and `move-object` rewrite envelope fields by line, and a
    docstring frontmatter block puts real YAML lines in the file, so both keep
    working on a Python object with no special case. A `HYDRA_OBJECT = {...}`
    dict would have needed its own writer.
    """

    def test_a_declared_field_can_be_rewritten_in_place(self):
        text, changed = envelopes.replace_envelope_field(
            _ENVELOPE, "hydra://engine-module/example", "schema_version", "4"
        )
        self.assertTrue(changed)
        self.assertIn("schema_version: 4\n", text)
        self.assertIn("Prose about the module.", text)

    def test_the_closing_delimiter_bounds_the_envelope_block(self):
        # Prose after the block is not part of the envelope, so a field-shaped
        # line down in the docstring body is out of reach.
        lines = _ENVELOPE.splitlines()
        anchor = envelopes.envelope_field_line_index(lines, "hydra_id", "hydra://engine-module/example")
        self.assertEqual(envelopes.envelope_block_end(lines, anchor, 0), lines.index("---", anchor))


if __name__ == "__main__":
    unittest.main()
