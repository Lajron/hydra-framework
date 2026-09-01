"""Mirror test for `hydra_engine.objects.discovery`."""

from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

_SRC = Path(__file__).resolve().parents[3] / "src"
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

from hydra_engine.objects import discovery  # noqa: E402


def _paths(root: Path) -> discovery.ObjectLocations:
    hydra = root / ".hydra-framework"
    return discovery.ObjectLocations(
        root=root,
        hydra=hydra,
        local=root / ".hydra-framework.local",
        personal_tasks_rel="tasks/personal",
        object_registry=hydra / "cognition/graph/registry.yaml",
    )


class CollectHydraObjectsTests(unittest.TestCase):
    def test_collects_frontmatter_object_with_derived_path_and_digest(self):
        root = Path(tempfile.mkdtemp(prefix="discovery-test-"))
        hydra = root / ".hydra-framework"
        hydra.mkdir(parents=True)
        (hydra / "obj.md").write_text(
            "---\nhydra_id: hydra://knowledge-unit/0001-test\nstatus: active\nscope: repo\nowners:\n  a: '2026-08-17'\n"
            "relations: []\nprovenance:\n  sources: []\n---\n# Title\n",
            encoding="utf-8",
        )
        objects, errors = discovery.collect_hydra_objects(_paths(root))
        self.assertEqual(errors, [])
        self.assertEqual(len(objects), 1)
        self.assertEqual(objects[0]["id"], "hydra://knowledge-unit/0001-test")

    def test_collects_sidecar_object_for_non_frontmatter_file(self):
        root = Path(tempfile.mkdtemp(prefix="discovery-test-"))
        hydra = root / ".hydra-framework"
        hydra.mkdir(parents=True)
        (hydra / "target.txt").write_text("payload\n", encoding="utf-8")
        (hydra / "sidecar.yaml").write_text(
            "schema: hydra-framework.object-sidecar.v1\n"
            "objects:\n"
            "  entry:\n"
            "    path: target.txt\n"
            "    title: Target\n"
            "    kind: source\n"
            "    hydra_id: hydra://source/0001-test\n"
            "    status: active\n"
            "    scope: repo\n"
            "    owners:\n"
            "      a: '2026-08-17'\n"
            "    relations: []\n"
            "    provenance:\n"
            "      sources: []\n",
            encoding="utf-8",
        )
        objects, errors = discovery.collect_hydra_objects(_paths(root))
        self.assertEqual(errors, [])
        ids = {obj["id"] for obj in objects}
        self.assertIn("hydra://source/0001-test", ids)

    def test_collects_an_engine_module_that_declares_an_envelope(self):
        # The Runtime/Engine family became matchable here: a `.py` module under
        # the engine source root is an object if, and only if, it declares an
        # envelope in its docstring.
        root = Path(tempfile.mkdtemp(prefix="discovery-test-"))
        module_dir = root / ".hydra-framework/engine/src/hydra_engine"
        module_dir.mkdir(parents=True)
        (module_dir / "registered.py").write_text(
            '"""---\nhydra_id: hydra://engine-module/registered\nkind: engine-module\n'
            "title: Registered\nstatus: active\nscope: base-seed\nowners:\n  team: hydra\n"
            'relations: []\nprovenance:\n  sources: []\n---\n\nProse.\n"""\n',
            encoding="utf-8",
        )
        (module_dir / "plain.py").write_text('"""Ordinary module."""\n', encoding="utf-8")
        objects, errors = discovery.collect_hydra_objects(_paths(root))
        self.assertEqual(errors, [])
        self.assertEqual([obj["id"] for obj in objects], ["hydra://engine-module/registered"])
        self.assertEqual(objects[0]["family"], "Runtime/Engine")
        self.assertEqual(objects[0]["missing_envelope_fields"], [])

    def test_extract_hydra_object_reports_invalid_yaml(self):
        root = Path(tempfile.mkdtemp(prefix="discovery-test-"))
        hydra = root / ".hydra-framework"
        hydra.mkdir(parents=True)
        path = hydra / "bad.yaml"
        path.write_text("body: |\n  block scalar\n", encoding="utf-8")
        obj, error = discovery.extract_hydra_object(path, _paths(root))
        self.assertIsNone(obj)
        self.assertIsNotNone(error)


if __name__ == "__main__":
    unittest.main()
