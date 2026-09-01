"""Mirror test for `hydra_engine.objects.store_queries`."""

from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

_SRC = Path(__file__).resolve().parents[3] / "src"
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

from hydra_engine.documents.tokens import write_text  # noqa: E402
from hydra_engine.identity.schema_versions import CURRENT_SCHEMA_VERSION  # noqa: E402
from hydra_engine.objects import discovery, registry, store_build, store_queries  # noqa: E402

UID = "11111111-1111-4111-8111-111111111111"


def _paths(root: Path) -> discovery.ObjectLocations:
    hydra = root / ".hydra-framework"
    return discovery.ObjectLocations(
        root=root, hydra=hydra, local=root / ".hydra-framework.local",
        personal_tasks_rel="tasks/personal", object_registry=hydra / "cognition/graph/registry.yaml",
    )


def _object_file(paths: discovery.ObjectLocations, rel: str, hydra_id: str, *, alias: str = "", relates_to: str = "", provenance_source: str = "") -> Path:
    path = paths.hydra / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    aliases = f"aliases:\n  - {alias}\n" if alias else ""
    relations = f"  - {relates_to}\n" if relates_to else ""
    sources = f"\n    - {provenance_source}" if provenance_source else " []"
    path.write_text(
        "---\n"
        f"hydra_id: {hydra_id}\n"
        f"uid: {UID}\n"
        f"schema_version: {CURRENT_SCHEMA_VERSION}\n"
        "kind: knowledge-unit\n"
        "title: Test Object\n"
        "status: active\n"
        "scope: base-seed\n"
        f"{aliases}"
        "owners:\n"
        "  team: hydra\n"
        "relations:\n" + relations +
        "provenance:\n"
        f"  sources:{sources}\n"
        "---\n# Test Object\n",
        encoding="utf-8",
    )
    return path


def _repo() -> discovery.ObjectLocations:
    root = Path(tempfile.mkdtemp(prefix="store-queries-"))
    return _paths(root)


def _index(paths: discovery.ObjectLocations) -> None:
    objects, errors = discovery.collect_hydra_objects(paths)
    assert not errors, errors
    write_text(paths.object_registry, registry.object_registry_text(objects))


class OpenFreshStoreTests(unittest.TestCase):
    def test_none_when_no_store_built(self):
        paths = _repo()
        self.assertIsNone(store_queries.open_fresh_store(paths, paths.local))

    def test_open_once_built_and_indexed(self):
        paths = _repo()
        _object_file(paths, "repo/knowledge-units/0001-a.md", "hydra://knowledge-unit/0001-a")
        _index(paths)
        store_build.rebuild_store(paths, paths.local)
        conn = store_queries.open_fresh_store(paths, paths.local)
        self.assertIsNotNone(conn)
        conn.close()

    def test_none_when_export_changed_since_the_store_was_built(self):
        paths = _repo()
        _object_file(paths, "repo/knowledge-units/0001-a.md", "hydra://knowledge-unit/0001-a")
        _index(paths)
        store_build.rebuild_store(paths, paths.local)

        _object_file(paths, "repo/knowledge-units/0002-b.md", "hydra://knowledge-unit/0002-b")
        _index(paths)

        self.assertIsNone(store_queries.open_fresh_store(paths, paths.local))

    def test_none_when_disabled_by_env_var(self):
        paths = _repo()
        _object_file(paths, "repo/knowledge-units/0001-a.md", "hydra://knowledge-unit/0001-a")
        _index(paths)
        store_build.rebuild_store(paths, paths.local)
        with mock.patch.dict("os.environ", {"HYDRA_QUERY_STORE": "off"}):
            self.assertIsNone(store_queries.open_fresh_store(paths, paths.local))


class ResolveTests(unittest.TestCase):
    def setUp(self):
        self.paths = _repo()
        _object_file(self.paths, "repo/knowledge-units/0001-a.md", "hydra://knowledge-unit/0001-a", alias="hydra://knowledge-unit/0001-old", relates_to="hydra://knowledge-unit/0002-b")
        _object_file(self.paths, "repo/knowledge-units/0002-b.md", "hydra://knowledge-unit/0002-b")
        _index(self.paths)
        store_build.rebuild_store(self.paths, self.paths.local)
        self.conn = store_queries.open_fresh_store(self.paths, self.paths.local)

    def tearDown(self):
        self.conn.close()

    def test_resolve_by_primary_id(self):
        obj = store_queries.resolve(self.conn, "hydra://knowledge-unit/0001-a")
        self.assertEqual(obj["hydra_id"], "hydra://knowledge-unit/0001-a")
        self.assertEqual(obj["resolved_from_alias"], "")
        self.assertEqual(obj["aliases"], ["hydra://knowledge-unit/0001-old"])
        self.assertEqual(obj["relations"], ["hydra://knowledge-unit/0002-b"])

    def test_resolve_by_alias(self):
        obj = store_queries.resolve(self.conn, "hydra://knowledge-unit/0001-old")
        self.assertEqual(obj["hydra_id"], "hydra://knowledge-unit/0001-a")
        self.assertEqual(obj["resolved_from_alias"], "hydra://knowledge-unit/0001-old")

    def test_resolve_unknown_ref_returns_none(self):
        self.assertIsNone(store_queries.resolve(self.conn, "hydra://knowledge-unit/9999-nope"))

    def test_by_uid_and_by_path(self):
        self.assertEqual({row["hydra_id"] for row in store_queries.by_uid(self.conn, UID)}, {"hydra://knowledge-unit/0001-a", "hydra://knowledge-unit/0002-b"})
        self.assertEqual([row["hydra_id"] for row in store_queries.by_path(self.conn, ".hydra-framework/repo/knowledge-units/0001-a.md")], ["hydra://knowledge-unit/0001-a"])


class CitersOfTests(unittest.TestCase):
    def test_finds_the_object_that_relates_to_the_target(self):
        paths = _repo()
        _object_file(paths, "repo/knowledge-units/0001-a.md", "hydra://knowledge-unit/0001-a", relates_to="hydra://knowledge-unit/0002-b")
        _object_file(paths, "repo/knowledge-units/0002-b.md", "hydra://knowledge-unit/0002-b")
        _index(paths)
        store_build.rebuild_store(paths, paths.local)
        conn = store_queries.open_fresh_store(paths, paths.local)
        self.assertEqual(store_queries.citers_of(conn, "hydra://knowledge-unit/0002-b"), ["hydra://knowledge-unit/0001-a"])
        self.assertEqual(store_queries.citers_of(conn, "hydra://knowledge-unit/0001-a"), [])
        conn.close()


class CitersOfSourcePathTests(unittest.TestCase):
    def test_finds_the_object_that_cites_the_path_as_provenance(self):
        paths = _repo()
        _object_file(
            paths, "repo/knowledge-units/0001-a.md", "hydra://knowledge-unit/0001-a",
            provenance_source=".hydra-framework/repo/knowledge-units/0002-b.md",
        )
        _object_file(paths, "repo/knowledge-units/0002-b.md", "hydra://knowledge-unit/0002-b")
        _index(paths)
        store_build.rebuild_store(paths, paths.local)
        conn = store_queries.open_fresh_store(paths, paths.local)
        self.assertEqual(
            store_queries.citers_of_source_path(conn, ".hydra-framework/repo/knowledge-units/0002-b.md"),
            ["hydra://knowledge-unit/0001-a"],
        )
        self.assertEqual(store_queries.citers_of_source_path(conn, ".hydra-framework/repo/knowledge-units/0001-a.md"), [])
        conn.close()


class ImpactTests(unittest.TestCase):
    def test_transitive_relations_within_depth(self):
        paths = _repo()
        _object_file(paths, "repo/knowledge-units/0001-a.md", "hydra://knowledge-unit/0001-a", relates_to="hydra://knowledge-unit/0002-b")
        _object_file(paths, "repo/knowledge-units/0002-b.md", "hydra://knowledge-unit/0002-b", relates_to="hydra://knowledge-unit/0003-c")
        _object_file(paths, "repo/knowledge-units/0003-c.md", "hydra://knowledge-unit/0003-c")
        _index(paths)
        store_build.rebuild_store(paths, paths.local)
        conn = store_queries.open_fresh_store(paths, paths.local)

        self.assertEqual(store_queries.impact(conn, "hydra://knowledge-unit/0001-a", depth=5), ["hydra://knowledge-unit/0002-b", "hydra://knowledge-unit/0003-c"])
        self.assertEqual(store_queries.impact(conn, "hydra://knowledge-unit/0001-a", depth=1), ["hydra://knowledge-unit/0002-b"])
        conn.close()

    def test_a_relation_cycle_terminates_instead_of_looping(self):
        paths = _repo()
        _object_file(paths, "repo/knowledge-units/0001-a.md", "hydra://knowledge-unit/0001-a", relates_to="hydra://knowledge-unit/0002-b")
        _object_file(paths, "repo/knowledge-units/0002-b.md", "hydra://knowledge-unit/0002-b", relates_to="hydra://knowledge-unit/0001-a")
        _index(paths)
        store_build.rebuild_store(paths, paths.local)
        conn = store_queries.open_fresh_store(paths, paths.local)

        self.assertEqual(store_queries.impact(conn, "hydra://knowledge-unit/0001-a", depth=10), ["hydra://knowledge-unit/0002-b"])
        conn.close()


if __name__ == "__main__":
    unittest.main()
