"""Mirror test for `hydra_engine.knowledge.context_packets`."""

from __future__ import annotations

import re
import sys
import tempfile
import unittest
from unittest import mock
from pathlib import Path

_SRC = Path(__file__).resolve().parents[3] / "src"
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

from hydra_engine.knowledge import context_packets  # noqa: E402
from hydra_engine.knowledge.packages import ContextCompilerPaths  # noqa: E402
from hydra_engine.objects.discovery import ObjectLocations  # noqa: E402

_DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")


def _resolver_paths(root: Path) -> ObjectLocations:
    hydra = root / ".hydra-framework"
    return ObjectLocations(
        root=root, hydra=hydra, local=root / ".hydra-framework.local",
        personal_tasks_rel="tasks/personal", object_registry=hydra / "cognition/graph/registry.yaml",
    )


class TodayTests(unittest.TestCase):
    def test_today_is_an_iso_date(self):
        self.assertRegex(context_packets.today(), _DATE_RE)


class CompileContextPacketTests(unittest.TestCase):
    def test_compiles_a_packet_with_an_explicit_path_reference(self):
        root = Path(tempfile.mkdtemp(prefix="context-packets-test-"))
        (root / ".hydra-framework").mkdir(parents=True)
        note = root / "note.md"
        note.write_text("some content\n", encoding="utf-8")
        paths = ContextCompilerPaths(root=root, hydra=root / ".hydra-framework")
        packet = context_packets.compile_context_packet(
            task="test task",
            paths=paths,
            resolver_paths=_resolver_paths(root),
            surface_totals={"approx_tokens": 0},
            surface_file_count=0,
            path_refs=["note.md"],
        )
        self.assertEqual(packet["schema"], "hydra-framework.context-packet.v1")
        self.assertEqual([c["path"] for c in packet["selected_context"]], ["note.md"])
        self.assertEqual(packet["warnings"], [])

    def test_missing_path_reference_is_a_warning(self):
        root = Path(tempfile.mkdtemp(prefix="context-packets-test-"))
        (root / ".hydra-framework").mkdir(parents=True)
        paths = ContextCompilerPaths(root=root, hydra=root / ".hydra-framework")
        packet = context_packets.compile_context_packet(
            task="test task",
            paths=paths,
            resolver_paths=_resolver_paths(root),
            surface_totals={"approx_tokens": 0},
            surface_file_count=0,
            path_refs=["missing.md"],
        )
        self.assertTrue(any("not found" in warning for warning in packet["warnings"]))

    def test_packet_contains_every_stage_zero_baseline_field(self):
        # Moved from `test_hydra.py`'s `ContextCompilerTests` -- was
        # asserted against the live repository;
        # this checks the packet's own shape instead, which needs no real tree.
        root = Path(tempfile.mkdtemp(prefix="context-packets-test-"))
        (root / ".hydra-framework").mkdir(parents=True)
        (root / "note.md").write_text("some content\n", encoding="utf-8")
        paths = ContextCompilerPaths(root=root, hydra=root / ".hydra-framework")
        packet = context_packets.compile_context_packet(
            task="test task",
            paths=paths,
            resolver_paths=_resolver_paths(root),
            surface_totals={"approx_tokens": 0},
            surface_file_count=0,
            provider="codex",
            model="gpt-5",
            budget=20000,
            path_refs=["note.md"],
        )
        for field in [
            "date", "generated_at", "task", "provider", "model", "packages",
            "selected_context", "omitted_candidates", "token_estimate",
        ]:
            self.assertIn(field, packet)
        self.assertEqual(packet["provider"], "codex")
        self.assertEqual(packet["model"], "gpt-5")

    def test_explicit_object_reference_carries_resolver_metadata(self):
        root = Path(tempfile.mkdtemp(prefix="context-packets-test-"))
        hydra = root / ".hydra-framework"
        obj_path = hydra / "knowledge-units/0001-test.md"
        obj_path.parent.mkdir(parents=True)
        obj_path.write_text(
            "---\nhydra_id: hydra://knowledge-unit/0001-test\nuid: 11111111-1111-4111-8111-111111111111\n"
            "schema_version: 3\nkind: knowledge-unit\ntitle: Test Object\nstatus: accepted\nscope: repo\n"
            "owners:\n  team: fixture\nrelations: []\nprovenance:\n  sources: []\n---\n# Test Object\n",
            encoding="utf-8",
        )
        paths = ContextCompilerPaths(root=root, hydra=hydra)
        packet = context_packets.compile_context_packet(
            task="test task",
            paths=paths,
            resolver_paths=_resolver_paths(root),
            surface_totals={"approx_tokens": 0},
            surface_file_count=0,
            object_refs=["hydra://knowledge-unit/0001-test"],
        )
        matches = [item for item in packet["selected_context"] if item.get("hydra_id") == "hydra://knowledge-unit/0001-test"]
        self.assertEqual(len(matches), 1)
        self.assertIn("digest", matches[0])
        self.assertEqual(matches[0]["status"], "accepted")

    def test_required_unit_larger_than_budget_is_still_selected(self):
        root = Path(tempfile.mkdtemp(prefix="context-packets-test-"))
        hydra = root / ".hydra-framework"
        pkg_root = hydra / "repo/knowledge/knowledge-packages/demo"
        (pkg_root / "units").mkdir(parents=True)
        (pkg_root / "overview.md").write_text("# Demo\n", encoding="utf-8")
        unit_text = (
            "---\nhydra_id: hydra://knowledge-unit/demo/big\nuid: 22222222-2222-4222-8222-222222222222\n"
            "schema_version: 3\nkind: knowledge-unit\nunit_kind: answer\ntitle: Big\nstatus: active\nscope: repo\n"
            "owners:\n  team: fixture\nrelations: []\nprovenance:\n  sources: []\n---\n"
            "# Big\n\n" + ("word " * 200) + "\n"
        )
        (pkg_root / "units" / "big.md").write_text(unit_text, encoding="utf-8")
        paths = ContextCompilerPaths(root=root, hydra=hydra)
        packet = context_packets.compile_context_packet(
            task="small",
            paths=paths,
            resolver_paths=_resolver_paths(root),
            surface_totals={"approx_tokens": 0},
            surface_file_count=0,
            budget=5,
            object_refs=["hydra://knowledge-unit/demo/big"],
        )
        self.assertEqual(len(packet["selected_context"]), 1)
        self.assertEqual(
            packet["selected_context"][0]["path"],
            ".hydra-framework/repo/knowledge/knowledge-packages/demo/units/big.md",
        )
        self.assertTrue(packet["selected_context"][0]["required"])
        self.assertGreater(packet["token_estimate"]["required_overage"], 0)
        self.assertEqual(packet["required_units"][0]["hydra_id"], "hydra://knowledge-unit/demo/big")
        # exit-code neutrality: nothing here is a hard failure, only a reported number
        self.assertNotIn("error", packet)

    def test_a_non_required_unit_candidate_can_still_be_omitted(self):
        root = Path(tempfile.mkdtemp(prefix="context-packets-test-"))
        hydra = root / ".hydra-framework"
        pkg_root = hydra / "repo/knowledge/knowledge-packages/demo"
        (pkg_root / "units").mkdir(parents=True)
        (pkg_root / "overview.md").write_text("# Demo\n", encoding="utf-8")
        unit_text = (
            "---\nhydra_id: hydra://knowledge-unit/demo/small\nuid: 33333333-3333-4333-8333-333333333333\n"
            "schema_version: 3\nkind: knowledge-unit\nunit_kind: answer\ntitle: Small\nstatus: active\nscope: repo\n"
            "owners:\n  team: fixture\nrelations: []\nprovenance:\n  sources: []\n---\n"
            "# Small\n\n" + ("word " * 200) + "\n"
        )
        (pkg_root / "units" / "small.md").write_text(unit_text, encoding="utf-8")
        paths = ContextCompilerPaths(root=root, hydra=hydra)
        packet = context_packets.compile_context_packet(
            task="small",
            paths=paths,
            resolver_paths=_resolver_paths(root),
            surface_totals={"approx_tokens": 0},
            surface_file_count=0,
            budget=1,
        )
        self.assertEqual(packet["selected_context"], [])
        self.assertTrue(any(o["path"].endswith("small.md") for o in packet["omitted_candidates"]))

    def test_omitted_stale_unit_keeps_stale_sources_for_reporting(self):
        root = Path(tempfile.mkdtemp(prefix="context-packets-test-"))
        hydra = root / ".hydra-framework"
        pkg_root = hydra / "repo/knowledge/knowledge-packages/demo"
        (pkg_root / "units").mkdir(parents=True)
        (pkg_root / "overview.md").write_text("# Demo\n", encoding="utf-8")
        (root / "source.py").write_text("x = 1\n", encoding="utf-8")
        (pkg_root / "units" / "stale.md").write_text(
            "---\nhydra_id: hydra://knowledge-unit/demo/stale\nuid: 44444444-4444-4444-8444-444444444444\n"
            "schema_version: 3\nkind: knowledge-unit\nunit_kind: answer\ntitle: Stale\nstatus: active\nscope: repo\n"
            "owners:\n  team: fixture\nrelations: []\nprovenance:\n  sources:\n    - source.py\n"
            "checked_on: 2000-01-01\n---\n# Stale\n\n" + ("word " * 200) + "\n",
            encoding="utf-8",
        )
        paths = ContextCompilerPaths(root=root, hydra=hydra)
        with mock.patch("hydra_engine.knowledge.freshness.git_port.last_commit_iso", return_value="2001-01-01T00:00:00+00:00"):
            packet = context_packets.compile_context_packet(
                task="stale",
                paths=paths,
                resolver_paths=_resolver_paths(root),
                surface_totals={"approx_tokens": 0},
                surface_file_count=0,
                budget=1,
            )
        self.assertEqual(packet["selected_context"], [])
        stale = [item for item in packet["omitted_candidates"] if item.get("stale_sources")]
        self.assertEqual(len(stale), 1)
        self.assertEqual(stale[0]["source"], "hydra://knowledge-unit/demo/stale")
        self.assertEqual(stale[0]["stale_sources"], ["source.py"])

    def test_task_not_matching_any_route_does_not_apply_route_semantics(self):
        root = Path(tempfile.mkdtemp(prefix="context-packets-test-"))
        hydra = root / ".hydra-framework"
        pkg_root = hydra / "repo/knowledge/knowledge-packages/demo"
        units_dir = pkg_root / "units"
        units_dir.mkdir(parents=True)

        def _unit(slug):
            (units_dir / f"{slug}.md").write_text(
                f"---\nhydra_id: hydra://knowledge-unit/demo/{slug}\nuid: 11111111-1111-4111-8111-11111111111{slug[-1]}\n"
                f"schema_version: 3\nkind: knowledge-unit\nunit_kind: answer\ntitle: {slug}\nstatus: active\nscope: repo\n"
                f"owners:\n  team: fixture\nrelations: []\nprovenance:\n  sources: []\nquestion: \"What about {slug}?\"\n"
                f"---\n\n# {slug}\n\n## Answer\n\nSomething.\n",
                encoding="utf-8",
            )

        _unit("adopt")
        (pkg_root / "routing.yaml").write_text(
            "schema: hydra-framework.package-routing.v2\n"
            "package: demo\ntitle: Demo\nkeywords: copied repository hydra\n\n"
            "routes:\n"
            "  adopt_into_repo:\n"
            "    use_when:\n"
            "      - Hydra was copied into a repository and needs wiring\n"
            "    priority_units:\n"
            "      - hydra://knowledge-unit/demo/adopt\n"
            "    avoid_by_default:\n"
            "      - the host repository's full source tree\n"
            "    verify:\n"
            "      - python3 .hydra-framework/scripts/hydra.py adopt\n",
            encoding="utf-8",
        )
        paths = ContextCompilerPaths(root=root, hydra=hydra)
        packet = context_packets.compile_context_packet(
            task="Completely unrelated topic about weather forecasting models.",
            paths=paths,
            resolver_paths=_resolver_paths(root),
            surface_totals={"approx_tokens": 0},
            surface_file_count=0,
            budget=20000,
            package_values=["demo"],
        )
        self.assertEqual(packet["avoid_by_default"], [])
        self.assertEqual(packet["verify"], [])
        self.assertEqual(packet["packages"][0]["route"], "")

    def test_task_matching_a_named_routes_use_when_auto_selects_it_without_route_flag(self):
        root = Path(tempfile.mkdtemp(prefix="context-packets-test-"))
        hydra = root / ".hydra-framework"
        pkg_root = hydra / "repo/knowledge/knowledge-packages/demo"
        units_dir = pkg_root / "units"
        units_dir.mkdir(parents=True)

        def _unit(slug):
            (units_dir / f"{slug}.md").write_text(
                f"---\nhydra_id: hydra://knowledge-unit/demo/{slug}\nuid: 11111111-1111-4111-8111-11111111111{slug[-1]}\n"
                f"schema_version: 3\nkind: knowledge-unit\nunit_kind: answer\ntitle: {slug}\nstatus: active\nscope: repo\n"
                f"owners:\n  team: fixture\nrelations: []\nprovenance:\n  sources: []\nquestion: \"What about {slug}?\"\n"
                f"---\n\n# {slug}\n\n## Answer\n\nSomething.\n",
                encoding="utf-8",
            )

        _unit("adopt")
        (pkg_root / "routing.yaml").write_text(
            "schema: hydra-framework.package-routing.v2\n"
            "package: demo\ntitle: Demo\nkeywords: copied repository hydra\n\n"
            "routes:\n"
            "  adopt_into_repo:\n"
            "    use_when:\n"
            "      - Hydra was copied into a repository and needs wiring\n"
            "    priority_units:\n"
            "      - hydra://knowledge-unit/demo/adopt\n"
            "    avoid_by_default:\n"
            "      - the host repository's full source tree\n"
            "    verify:\n"
            "      - python3 .hydra-framework/scripts/hydra.py adopt\n",
            encoding="utf-8",
        )
        paths = ContextCompilerPaths(root=root, hydra=hydra)
        packet = context_packets.compile_context_packet(
            task="Hydra was copied into this repository and needs wiring.",
            paths=paths,
            resolver_paths=_resolver_paths(root),
            surface_totals={"approx_tokens": 0},
            surface_file_count=0,
            budget=20000,
            package_values=["demo"],
        )
        self.assertEqual(packet["avoid_by_default"], ["the host repository's full source tree"])
        self.assertEqual(packet["verify"], ["python3 .hydra-framework/scripts/hydra.py adopt"])
        self.assertEqual(packet["packages"][0]["route"], "adopt_into_repo")

    def test_explicit_route_narrows_units_to_priority_units_and_requires(self):
        root = Path(tempfile.mkdtemp(prefix="context-packets-test-"))
        hydra = root / ".hydra-framework"
        pkg_root = hydra / "repo/knowledge/knowledge-packages/demo"
        units_dir = pkg_root / "units"
        units_dir.mkdir(parents=True)

        def _unit(slug, extra=""):
            (units_dir / f"{slug}.md").write_text(
                f"---\nhydra_id: hydra://knowledge-unit/demo/{slug}\nuid: 11111111-1111-4111-8111-11111111111{slug[-1]}\n"
                f"schema_version: 3\nkind: knowledge-unit\nunit_kind: answer\ntitle: {slug}\nstatus: active\nscope: repo\n"
                f"owners:\n  team: fixture\nrelations: []\nprovenance:\n  sources: []\nquestion: \"What about {slug}?\"\n"
                f"{extra}---\n\n# {slug}\n\n## Answer\n\nSomething.\n",
                encoding="utf-8",
            )

        _unit("routed")
        _unit("required")
        _unit("irrelevant")
        (pkg_root / "routing.yaml").write_text(
            "schema: hydra-framework.package-routing.v2\n"
            "package: demo\ntitle: Demo\nkeywords: routing test keyword\n\n"
            "routes:\n"
            "  main_route:\n"
            "    use_when:\n"
            "      - routing test keyword\n"
            "    priority_units:\n"
            "      - hydra://knowledge-unit/demo/routed\n"
            "    requires:\n"
            "      - hydra://knowledge-unit/demo/required\n"
            "    avoid_by_default:\n"
            "      - generated/**\n"
            "    verify:\n"
            "      - echo ok\n",
            encoding="utf-8",
        )
        paths = ContextCompilerPaths(root=root, hydra=hydra)
        packet = context_packets.compile_context_packet(
            task="routing test keyword",
            paths=paths,
            resolver_paths=_resolver_paths(root),
            surface_totals={"approx_tokens": 0},
            surface_file_count=0,
            budget=20000,
            route_values=["demo:main_route"],
        )
        selected_ids = {c.get("source") for c in packet["selected_context"] if c["kind"] == "knowledge-unit"}
        self.assertEqual(selected_ids, {"hydra://knowledge-unit/demo/routed", "hydra://knowledge-unit/demo/required"})
        self.assertEqual(packet["avoid_by_default"], ["generated/**"])
        self.assertEqual(packet["verify"], ["echo ok"])
        self.assertEqual(packet["packages"][0]["route"], "main_route")
        required_flags = {c["path"]: c["required"] for c in packet["selected_context"] if c["kind"] == "knowledge-unit"}
        self.assertTrue(any(v for v in required_flags.values()))

    def test_budget_of_one_omits_the_candidate_without_exceeding_selection(self):
        root = Path(tempfile.mkdtemp(prefix="context-packets-test-"))
        (root / ".hydra-framework").mkdir(parents=True)
        (root / "note.md").write_text("some content well over one token\n", encoding="utf-8")
        paths = ContextCompilerPaths(root=root, hydra=root / ".hydra-framework")
        packet = context_packets.compile_context_packet(
            task="test task",
            paths=paths,
            resolver_paths=_resolver_paths(root),
            surface_totals={"approx_tokens": 0},
            surface_file_count=0,
            budget=1,
            path_refs=["note.md"],
        )
        self.assertEqual(packet["selected_context"], [])
        self.assertTrue(packet["omitted_candidates"])
        self.assertEqual(packet["token_estimate"]["selected_context"], 0)


if __name__ == "__main__":
    unittest.main()
