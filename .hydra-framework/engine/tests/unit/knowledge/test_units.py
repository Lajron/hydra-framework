"""Mirror test for `hydra_engine.knowledge.units`."""

from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

_SRC = Path(__file__).resolve().parents[3] / "src"
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

from hydra_engine.knowledge import units  # noqa: E402

def _write_unit(root: Path, slug: str) -> Path:
    root.mkdir(parents=True, exist_ok=True)
    text = f"""---
hydra_id: hydra://knowledge-unit/demo/{slug}
uid: 11111111-1111-4111-8111-111111111111
schema_version: 3
kind: knowledge-unit
unit_kind: answer
title: Demo Unit
status: active
scope: repo
owners:
  team: fixture
relations: []
provenance:
  sources:
    - some/source.py
question: "What does this demo unit answer?"
group: demo
certainty: confirmed
checked_on: 2026-08-23
reads:
  - some/source.py
requires: []
see_also: []
verify:
  - echo ok
expand_when:
  - when: "a thing happens"
---

# Demo Unit

## Answer

It answers the demo question.
"""
    path = root / f"{slug}.md"
    path.write_text(text, encoding="utf-8")
    return path


class DiscoveryTests(unittest.TestCase):
    def test_units_root_is_a_units_subdirectory(self):
        package_root = Path("/tmp/example-package")
        self.assertEqual(units.units_root(package_root), package_root / "units")

    def test_discover_unit_paths_is_empty_when_no_units_dir(self):
        package_root = Path(tempfile.mkdtemp(prefix="units-test-"))
        self.assertEqual(units.discover_unit_paths(package_root), [])

    def test_discover_unit_paths_is_sorted(self):
        package_root = Path(tempfile.mkdtemp(prefix="units-test-"))
        _write_unit(units.units_root(package_root), "zeta")
        _write_unit(units.units_root(package_root), "alpha")
        found = units.discover_unit_paths(package_root)
        self.assertEqual([p.stem for p in found], ["alpha", "zeta"])


class ReadUnitTests(unittest.TestCase):
    def test_happy_path_reads_every_field(self):
        repo_root = Path(tempfile.mkdtemp(prefix="units-test-"))
        path = _write_unit(repo_root / "units", "happy")
        unit = units.read_unit(path, repo_root)
        self.assertIsNotNone(unit)
        self.assertEqual(unit.hydra_id, "hydra://knowledge-unit/demo/happy")
        self.assertEqual(unit.unit_kind, "answer")
        self.assertEqual(unit.question, "What does this demo unit answer?")
        self.assertEqual(unit.reads, ("some/source.py",))
        self.assertEqual(unit.sources, ("some/source.py",))
        self.assertEqual(unit.source_digests, ())
        self.assertEqual(len(unit.expand_when), 1)
        self.assertEqual(unit.expand_when[0]["when"], "a thing happens")

    def test_reads_source_digests_without_changing_sources_shape(self):
        repo_root = Path(tempfile.mkdtemp(prefix="units-test-"))
        path = repo_root / "units" / "fingerprinted.md"
        path.parent.mkdir(parents=True)
        path.write_text(
            "---\nhydra_id: hydra://knowledge-unit/demo/fingerprinted\nkind: knowledge-unit\n"
            "provenance:\n  sources:\n    - some/source.py\n  source_digests:\n"
            "    - source: some/source.py\n      digest: sha256:aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa\n"
            "---\n# Fingerprinted\n",
            encoding="utf-8",
        )
        unit = units.read_unit(path, repo_root)
        self.assertEqual(unit.sources, ("some/source.py",))
        self.assertEqual(
            unit.source_digests,
            [{"source": "some/source.py", "digest": "sha256:" + ("a" * 64)}],
        )

    def test_no_frontmatter_returns_none(self):
        repo_root = Path(tempfile.mkdtemp(prefix="units-test-"))
        path = repo_root / "units" / "plain.md"
        path.parent.mkdir(parents=True)
        path.write_text("# Just prose\n", encoding="utf-8")
        self.assertIsNone(units.read_unit(path, repo_root))

    def test_wrong_kind_returns_none(self):
        repo_root = Path(tempfile.mkdtemp(prefix="units-test-"))
        path = repo_root / "units" / "wrong-kind.md"
        path.parent.mkdir(parents=True)
        path.write_text(
            "---\nhydra_id: hydra://knowledge-slice/demo/x\nkind: knowledge-slice\n---\n# X\n",
            encoding="utf-8",
        )
        self.assertIsNone(units.read_unit(path, repo_root))

    def test_missing_optional_fields_give_empty_tuples(self):
        repo_root = Path(tempfile.mkdtemp(prefix="units-test-"))
        path = repo_root / "units" / "sparse.md"
        path.parent.mkdir(parents=True)
        path.write_text(
            "---\nhydra_id: hydra://knowledge-unit/demo/sparse\nkind: knowledge-unit\n---\n# Sparse\n",
            encoding="utf-8",
        )
        unit = units.read_unit(path, repo_root)
        self.assertEqual(unit.reads, ())
        self.assertEqual(unit.requires, ())
        self.assertEqual(unit.see_also, ())
        self.assertEqual(unit.verify, ())
        self.assertEqual(unit.expand_when, ())
        self.assertEqual(unit.sources, ())
        self.assertEqual(unit.question, "")


class UnitsByIdTests(unittest.TestCase):
    def test_indexes_by_hydra_id(self):
        repo_root = Path(tempfile.mkdtemp(prefix="units-test-"))
        _write_unit(repo_root / "units", "one")
        by_id = units.units_by_id(repo_root, repo_root)
        self.assertIn("hydra://knowledge-unit/demo/one", by_id)


class RequiredSeedIdsTests(unittest.TestCase):
    def test_object_refs_are_seeds(self):
        seeds = units.required_seed_ids(None, ["hydra://knowledge-unit/demo/one"])
        self.assertEqual(seeds, {"hydra://knowledge-unit/demo/one"})

    def test_pack_read_bullets_contribute_seeds(self):
        pack = {"read": ["see hydra://knowledge-unit/demo/two for details"]}
        seeds = units.required_seed_ids(pack, [])
        self.assertEqual(seeds, {"hydra://knowledge-unit/demo/two"})


class RequiredClosureTests(unittest.TestCase):
    def test_transitive_requires_are_included(self):
        by_id = {
            "hydra://knowledge-unit/demo/a": units.Unit(
                path=Path("a.md"), hydra_id="hydra://knowledge-unit/demo/a", unit_kind="answer",
                title="A", question="", group="", certainty="", checked_on="",
                reads=(), requires=("hydra://knowledge-unit/demo/b",), see_also=(), verify=(),
                expand_when=(), sources=(),
            ),
            "hydra://knowledge-unit/demo/b": units.Unit(
                path=Path("b.md"), hydra_id="hydra://knowledge-unit/demo/b", unit_kind="answer",
                title="B", question="", group="", certainty="", checked_on="",
                reads=(), requires=(), see_also=(), verify=(), expand_when=(), sources=(),
            ),
        }
        warnings: list[str] = []
        closure = units.required_closure(by_id, {"hydra://knowledge-unit/demo/a"}, warnings)
        self.assertEqual(closure, {"hydra://knowledge-unit/demo/a", "hydra://knowledge-unit/demo/b"})
        self.assertEqual(warnings, [])

    def test_a_cycle_warns_and_terminates(self):
        by_id = {
            "hydra://knowledge-unit/demo/a": units.Unit(
                path=Path("a.md"), hydra_id="hydra://knowledge-unit/demo/a", unit_kind="answer",
                title="A", question="", group="", certainty="", checked_on="",
                reads=(), requires=("hydra://knowledge-unit/demo/b",), see_also=(), verify=(),
                expand_when=(), sources=(),
            ),
            "hydra://knowledge-unit/demo/b": units.Unit(
                path=Path("b.md"), hydra_id="hydra://knowledge-unit/demo/b", unit_kind="answer",
                title="B", question="", group="", certainty="", checked_on="",
                reads=(), requires=("hydra://knowledge-unit/demo/a",), see_also=(), verify=(),
                expand_when=(), sources=(),
            ),
        }
        warnings: list[str] = []
        closure = units.required_closure(by_id, {"hydra://knowledge-unit/demo/a"}, warnings)
        self.assertEqual(closure, {"hydra://knowledge-unit/demo/a", "hydra://knowledge-unit/demo/b"})
        self.assertTrue(any("cycle" in w for w in warnings))

    def test_a_diamond_is_not_reported_as_a_cycle(self):
        by_id = {
            "hydra://knowledge-unit/demo/a": units.Unit(
                path=Path("a.md"), hydra_id="hydra://knowledge-unit/demo/a", unit_kind="answer",
                title="A", question="", group="", certainty="", checked_on="",
                reads=(), requires=("hydra://knowledge-unit/demo/b", "hydra://knowledge-unit/demo/c"),
                see_also=(), verify=(), expand_when=(), sources=(),
            ),
            "hydra://knowledge-unit/demo/b": units.Unit(
                path=Path("b.md"), hydra_id="hydra://knowledge-unit/demo/b", unit_kind="answer",
                title="B", question="", group="", certainty="", checked_on="",
                reads=(), requires=("hydra://knowledge-unit/demo/d",), see_also=(), verify=(),
                expand_when=(), sources=(),
            ),
            "hydra://knowledge-unit/demo/c": units.Unit(
                path=Path("c.md"), hydra_id="hydra://knowledge-unit/demo/c", unit_kind="answer",
                title="C", question="", group="", certainty="", checked_on="",
                reads=(), requires=("hydra://knowledge-unit/demo/d",), see_also=(), verify=(),
                expand_when=(), sources=(),
            ),
            "hydra://knowledge-unit/demo/d": units.Unit(
                path=Path("d.md"), hydra_id="hydra://knowledge-unit/demo/d", unit_kind="answer",
                title="D", question="", group="", certainty="", checked_on="",
                reads=(), requires=(), see_also=(), verify=(), expand_when=(), sources=(),
            ),
        }
        warnings: list[str] = []
        closure = units.required_closure(by_id, {"hydra://knowledge-unit/demo/a"}, warnings)
        self.assertEqual(
            closure,
            {
                "hydra://knowledge-unit/demo/a", "hydra://knowledge-unit/demo/b",
                "hydra://knowledge-unit/demo/c", "hydra://knowledge-unit/demo/d",
            },
        )
        self.assertEqual(warnings, [])

    def test_missing_unit_in_closure_stops_without_error(self):
        warnings: list[str] = []
        closure = units.required_closure({}, {"hydra://knowledge-unit/demo/ghost"}, warnings)
        self.assertEqual(closure, {"hydra://knowledge-unit/demo/ghost"})
        self.assertEqual(warnings, [])


if __name__ == "__main__":
    unittest.main()
