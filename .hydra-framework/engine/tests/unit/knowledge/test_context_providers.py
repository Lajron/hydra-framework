"""Mirror test for `hydra_engine.knowledge.context_providers`."""

from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

_SRC = Path(__file__).resolve().parents[3] / "src"
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

from hydra_engine.identity.object_families import OBJECT_FAMILIES  # noqa: E402
from hydra_engine.knowledge import context_providers  # noqa: E402
from hydra_engine.knowledge.packages import ContextCompilerPaths  # noqa: E402
from hydra_engine.knowledge.search_index import SearchDocument, SearchResult  # noqa: E402
from hydra_engine.objects.discovery import ObjectLocations  # noqa: E402


def _resolver_paths(root: Path) -> ObjectLocations:
    hydra = root / ".hydra-framework"
    return ObjectLocations(
        root=root, hydra=hydra, local=root / ".hydra-framework.local",
        personal_tasks_rel="tasks/personal", object_registry=hydra / "cognition/graph/registry.yaml",
    )


def _request(
    root: Path,
    *,
    task: str = "",
    family_cap: int = context_providers.DEFAULT_FAMILY_CANDIDATE_CAP,
    search_results: tuple = (),
    package_values: tuple[str, ...] = (),
    route_values: tuple[str, ...] = (),
) -> context_providers.ProviderRequest:
    paths = ContextCompilerPaths(root=root, hydra=root / ".hydra-framework")
    kwargs = {
        "task": task,
        "paths": paths,
        "resolver_paths": _resolver_paths(root),
        "object_seed_ids": frozenset(),
        "chars_per_token": 4,
        "family_cap": family_cap,
        "search_results": search_results,
        "package_values": package_values,
    }
    if route_values:
        kwargs["route_values"] = route_values
    return context_providers.ProviderRequest(
        **kwargs,
    )


def _doc(path: str, *, kind: str, hydra_id: str = "") -> SearchDocument:
    return SearchDocument(
        key=path, hydra_id=hydra_id, aliases=(), path=path, kind=kind, package="",
        title=path, keywords=(), routes=(), use_when=(), headings=(), body="fixture body", relations=(),
    )


def _seed_unit(pkg_root: Path, slug: str, *, title: str = "") -> None:
    (pkg_root / "units" / f"{slug}.md").write_text(
        f"---\nhydra_id: hydra://knowledge-unit/demo/{slug}\nuid: 11111111-1111-4111-8111-11111111111{slug[-1]}\n"
        f"schema_version: 3\nkind: knowledge-unit\nunit_kind: answer\ntitle: {title or slug}\nstatus: active\nscope: repo\n"
        f"owners:\n  team: fixture\nrelations: []\nprovenance:\n  sources: []\nquestion: \"What about {slug}?\"\n"
        f"---\n\n# {title or slug}\n\n## Answer\n\nSomething about {title or slug}.\n",
        encoding="utf-8",
    )


def _seed_routed_package(root: Path) -> Path:
    pkg_root = root / ".hydra-framework/repo/knowledge/knowledge-packages/demo"
    (pkg_root / "units").mkdir(parents=True)
    (pkg_root / "overview.md").write_text("# Demo\n", encoding="utf-8")
    _seed_unit(pkg_root, "adopt")
    _seed_unit(pkg_root, "required")
    _seed_unit(pkg_root, "routing")
    (pkg_root / "routing.yaml").write_text(
        "schema: hydra-framework.package-routing.v2\n"
        "package: demo\ntitle: Demo\nkeywords:\n  - hydra\n\n"
        "routes:\n"
        "  adopt_into_repo:\n"
        "    use_when:\n"
        "      - Hydra was copied into a repository and needs wiring\n"
        "    priority_units:\n"
        "      - hydra://knowledge-unit/demo/adopt\n"
        "    requires:\n"
        "      - hydra://knowledge-unit/demo/required\n"
        "    avoid_by_default:\n"
        "      - the host repository's full source tree\n"
        "    verify:\n"
        "      - python3 .hydra-framework/scripts/hydra.py adopt\n",
        encoding="utf-8",
    )
    return pkg_root


class RegistryConsistencyTests(unittest.TestCase):
    def test_every_object_family_has_exactly_one_context_provider(self):
        self.assertEqual(
            {family.name for family in OBJECT_FAMILIES},
            {provider.family for provider in context_providers.CONTEXT_PROVIDERS},
        )
        families = [provider.family for provider in context_providers.CONTEXT_PROVIDERS]
        self.assertEqual(len(families), len(set(families)))


class MatchedFamiliesTests(unittest.TestCase):
    def test_matches_a_family_by_slug(self):
        matched, unknown = context_providers._matched_families(("runtime-engine",))
        self.assertEqual(matched, {"Runtime/Engine"})
        self.assertEqual(unknown, [])

    def test_matches_a_family_by_its_own_name(self):
        matched, unknown = context_providers._matched_families(("Source",))
        self.assertEqual(matched, {"Source"})
        self.assertEqual(unknown, [])

    def test_unrecognized_value_is_reported_unknown(self):
        matched, unknown = context_providers._matched_families(("not-a-real-family",))
        self.assertEqual(matched, set())
        self.assertEqual(unknown, ["not-a-real-family"])


class FamilySearchCollectorTests(unittest.TestCase):
    def test_filters_by_family_caps_and_sets_rank(self):
        root = Path(tempfile.mkdtemp(prefix="context-providers-test-"))
        hydra = root / ".hydra-framework"
        source_dir = hydra / "repo/source"
        source_dir.mkdir(parents=True)
        for slug in ("a", "b", "c"):
            (source_dir / f"{slug}.md").write_text(f"# {slug}\n", encoding="utf-8")
        capability_path = hydra / "capabilities/skill.md"
        capability_path.parent.mkdir(parents=True)
        capability_path.write_text("# skill\n", encoding="utf-8")

        results = (
            SearchResult(_doc(".hydra-framework/repo/source/a.md", kind="source"), "exact", 0),
            SearchResult(_doc(".hydra-framework/capabilities/skill.md", kind="capability"), "exact", 1),
            SearchResult(_doc(".hydra-framework/repo/source/b.md", kind="source"), "fts", 2),
            SearchResult(_doc(".hydra-framework/repo/source/c.md", kind="source"), "fts", 3),
        )
        request = _request(root, family_cap=2, search_results=results)
        output = context_providers.PROVIDERS_BY_FAMILY["Source"].collect(request)

        self.assertEqual(len(output.candidates), 2)
        self.assertEqual(
            [c["path"] for c in output.candidates],
            [".hydra-framework/repo/source/a.md", ".hydra-framework/repo/source/b.md"],
        )
        self.assertEqual([c["rank"] for c in output.candidates], [0, 2])
        self.assertTrue(all(c["kind"] == "context-provider-source" for c in output.candidates))

    def test_a_result_with_no_path_or_a_missing_file_is_skipped(self):
        root = Path(tempfile.mkdtemp(prefix="context-providers-test-"))
        results = (
            SearchResult(_doc("", kind="source"), "exact", 0),
            SearchResult(_doc(".hydra-framework/repo/source/missing.md", kind="source"), "exact", 0),
        )
        request = _request(root, search_results=results)
        output = context_providers.PROVIDERS_BY_FAMILY["Source"].collect(request)
        self.assertEqual(output.candidates, [])


class KnowledgeCollectorRouteAuthorityTests(unittest.TestCase):
    def test_task_matching_no_route_falls_back_to_search_fill(self):
        # A task with no term overlap against any route's `use_when` must
        # not activate route semantics -- it should fall through to
        # `_rank_no_route_units` exactly as before this fix.
        root = Path(tempfile.mkdtemp(prefix="context-providers-test-"))
        _seed_routed_package(root)
        request = _request(
            root,
            task="Completely unrelated topic about weather forecasting models.",
            package_values=("demo",),
        )

        output = context_providers.PROVIDERS_BY_FAMILY["Knowledge"].collect(request)

        self.assertEqual(output.avoid_by_default, [])
        self.assertEqual(output.verify, [])
        self.assertEqual(output.packages[0]["route"], "")

    def test_task_matching_a_named_routes_use_when_auto_selects_it(self):
        # The bug this fixes: without an explicit --route flag,
        # `_collect_knowledge` used to always fall back to generic
        # search-fill even when the task text clearly matched a named
        # route's `use_when`. It must now call `select_route` first and use
        # the match, the same as an explicit `--route` request would.
        root = Path(tempfile.mkdtemp(prefix="context-providers-test-"))
        _seed_routed_package(root)
        request = _request(
            root,
            task="Hydra was copied into this repository and needs wiring.",
            package_values=("demo",),
        )

        output = context_providers.PROVIDERS_BY_FAMILY["Knowledge"].collect(request)

        selected_ids = {candidate.get("source") for candidate in output.candidates if candidate["kind"] == "knowledge-unit"}
        self.assertEqual(selected_ids, {"hydra://knowledge-unit/demo/adopt", "hydra://knowledge-unit/demo/required"})
        self.assertEqual(output.avoid_by_default, ["the host repository's full source tree"])
        self.assertEqual(output.verify, ["python3 .hydra-framework/scripts/hydra.py adopt"])
        self.assertEqual(output.packages[0]["route"], "adopt_into_repo")

    def test_explicit_route_wins_over_auto_matching(self):
        # An explicit `--route` request must still take priority: it is
        # honored even when the task text alone would not have triggered
        # `select_route` at all.
        root = Path(tempfile.mkdtemp(prefix="context-providers-test-"))
        _seed_routed_package(root)
        request = _request(
            root,
            task="Completely unrelated topic about weather forecasting models.",
            package_values=("demo",),
            route_values=("demo:adopt_into_repo",),
        )

        output = context_providers.PROVIDERS_BY_FAMILY["Knowledge"].collect(request)

        selected_ids = {candidate.get("source") for candidate in output.candidates if candidate["kind"] == "knowledge-unit"}
        self.assertEqual(selected_ids, {"hydra://knowledge-unit/demo/adopt", "hydra://knowledge-unit/demo/required"})
        self.assertEqual(output.packages[0]["route"], "adopt_into_repo")

    def test_explicit_named_route_applies_priority_requires_avoid_and_verify(self):
        root = Path(tempfile.mkdtemp(prefix="context-providers-test-"))
        _seed_routed_package(root)
        request = _request(
            root,
            task="Adopt Hydra into this repository.",
            package_values=("demo",),
            route_values=("demo:adopt_into_repo",),
        )

        output = context_providers.PROVIDERS_BY_FAMILY["Knowledge"].collect(request)

        selected_ids = {candidate.get("source") for candidate in output.candidates if candidate["kind"] == "knowledge-unit"}
        self.assertEqual(selected_ids, {"hydra://knowledge-unit/demo/adopt", "hydra://knowledge-unit/demo/required"})
        self.assertEqual(output.avoid_by_default, ["the host repository's full source tree"])
        self.assertEqual(output.verify, ["python3 .hydra-framework/scripts/hydra.py adopt"])
        self.assertEqual(output.packages[0]["route"], "adopt_into_repo")

    def test_no_route_unit_selection_uses_search_rank_instead_of_alphabetical_order(self):
        root = Path(tempfile.mkdtemp(prefix="context-providers-test-"))
        pkg_root = root / ".hydra-framework/repo/knowledge/knowledge-packages/demo"
        (pkg_root / "units").mkdir(parents=True)
        (pkg_root / "overview.md").write_text("# Demo\n", encoding="utf-8")
        (pkg_root / "routing.yaml").write_text(
            "schema: hydra-framework.package-routing.v2\n"
            "package: demo\ntitle: Demo\nkeywords:\n  - ranking\n",
            encoding="utf-8",
        )
        _seed_unit(pkg_root, "alpha", title="Alphabetical")
        _seed_unit(pkg_root, "beta", title="Ranked")
        results = (
            SearchResult(_doc(
                ".hydra-framework/repo/knowledge/knowledge-packages/demo/units/beta.md",
                kind="knowledge-unit",
                hydra_id="hydra://knowledge-unit/demo/beta",
            ), "fts", 0),
            SearchResult(_doc(
                ".hydra-framework/repo/knowledge/knowledge-packages/demo/units/alpha.md",
                kind="knowledge-unit",
                hydra_id="hydra://knowledge-unit/demo/alpha",
            ), "fts", 1),
        )
        request = _request(
            root,
            task="ranking",
            family_cap=1,
            search_results=results,
            package_values=("demo",),
        )

        output = context_providers.PROVIDERS_BY_FAMILY["Knowledge"].collect(request)

        unit_paths = [candidate["path"] for candidate in output.candidates if candidate["kind"] == "knowledge-unit"]
        self.assertEqual(unit_paths, [".hydra-framework/repo/knowledge/knowledge-packages/demo/units/beta.md"])


class RunContextProvidersTests(unittest.TestCase):
    def test_knowledge_only_invokes_shared_search_for_ranked_unit_selection(self):
        root = Path(tempfile.mkdtemp(prefix="context-providers-test-"))
        (root / ".hydra-framework").mkdir(parents=True)
        request = _request(root, task="anything")
        with mock.patch(
            "hydra_engine.knowledge.context_providers.search_documents",
            return_value=((), None, "source"),
        ) as fake_search:
            output = context_providers.run_context_providers(request, include_families=("Knowledge",))
        fake_search.assert_called_once()
        self.assertEqual(output.candidates, [])
        self.assertEqual(output.packages, [])

    def test_a_search_family_triggers_exactly_one_search_call(self):
        root = Path(tempfile.mkdtemp(prefix="context-providers-test-"))
        (root / ".hydra-framework").mkdir(parents=True)
        request = _request(root, task="anything")
        with mock.patch(
            "hydra_engine.knowledge.context_providers.search_documents",
            return_value=((), None, "source"),
        ) as fake_search:
            context_providers.run_context_providers(
                request, include_families=("Source", "Capability", "Work"),
            )
        fake_search.assert_called_once()

    def test_unknown_family_is_a_warning_and_contributes_nothing(self):
        root = Path(tempfile.mkdtemp(prefix="context-providers-test-"))
        (root / ".hydra-framework").mkdir(parents=True)
        request = _request(root, task="anything")
        output = context_providers.run_context_providers(request, include_families=("not-a-real-family",))
        self.assertIn("Unknown context-provider family: not-a-real-family", output.warnings)
        self.assertEqual(output.candidates, [])

    def test_excluding_knowledge_drops_its_candidates(self):
        root = Path(tempfile.mkdtemp(prefix="context-providers-test-"))
        hydra = root / ".hydra-framework"
        pkg_root = hydra / "repo/knowledge/knowledge-packages/demo"
        pkg_root.mkdir(parents=True)
        (pkg_root / "overview.md").write_text("# Demo\n", encoding="utf-8")
        request = _request(root, task="demo", family_cap=0)
        included = context_providers.run_context_providers(request, include_families=("Knowledge",))
        excluded = context_providers.run_context_providers(request, exclude_families=("Knowledge",))
        self.assertTrue(any(c["kind"] == "package-overview" for c in included.candidates))
        self.assertEqual(excluded.packages, [])
        self.assertFalse(any(c["kind"] == "package-overview" for c in excluded.candidates))


if __name__ == "__main__":
    unittest.main()
