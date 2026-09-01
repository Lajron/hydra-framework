"""Mirror test for `hydra_engine.knowledge.routing`."""

from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

_SRC = Path(__file__).resolve().parents[3] / "src"
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

from hydra_engine.knowledge import packages, routing  # noqa: E402
from hydra_engine.objects.discovery import ObjectLocations  # noqa: E402


def _context_paths(root: Path) -> packages.ContextCompilerPaths:
    return packages.ContextCompilerPaths(root=root, hydra=root / ".hydra-framework")


def _resolver_paths(root: Path) -> ObjectLocations:
    hydra = root / ".hydra-framework"
    return ObjectLocations(
        root=root, hydra=hydra, local=root / ".hydra-framework.local",
        personal_tasks_rel="tasks/personal", object_registry=hydra / "cognition/graph/registry.yaml",
    )


def _make_package(root: Path, name: str, *, keywords: str = "alpha") -> None:
    pkg = root / ".hydra-framework/repo/knowledge/knowledge-packages" / name
    pkg.mkdir(parents=True)
    (pkg / "overview.md").write_text("# Overview\n", encoding="utf-8")
    (pkg / "routing.yaml").write_text(
        f"schema: {routing.ROUTING_SCHEMA}\npackage: {name}\ntitle: {name.title()}\nkeywords: {keywords}\n",
        encoding="utf-8",
    )


class RoutePackagesTests(unittest.TestCase):
    def test_routes_by_explicit_package_name(self):
        root = Path(tempfile.mkdtemp(prefix="routing-test-"))
        _make_package(root, "example")
        selected, warnings = routing.route_packages(
            "irrelevant prompt", ["example"], "", _context_paths(root), _resolver_paths(root)
        )
        self.assertEqual(warnings, [])
        self.assertEqual([item["package"] for item in selected], ["example"])

    def test_falls_back_to_the_only_package_when_nothing_requested(self):
        root = Path(tempfile.mkdtemp(prefix="routing-test-"))
        _make_package(root, "solo")
        selected, warnings = routing.route_packages("prompt", [], "", _context_paths(root), _resolver_paths(root))
        self.assertEqual([item["package"] for item in selected], ["solo"])
        self.assertEqual(selected[0]["reason"], "only knowledge package available")

    def test_unroutable_package_request_is_a_warning(self):
        root = Path(tempfile.mkdtemp(prefix="routing-test-"))
        selected, warnings = routing.route_packages("prompt", ["missing"], "", _context_paths(root), _resolver_paths(root))
        self.assertEqual(selected, [])
        self.assertTrue(any("not found or not routable" in warning for warning in warnings))

    def test_implicit_selection_is_token_matched_not_substring(self):
        # F: `hydra` matched `dehydrated` under raw substring containment.
        # Two packages so the single-package fallback cannot mask the result.
        root = Path(tempfile.mkdtemp(prefix="routing-test-"))
        _make_package(root, "example", keywords="hydra")
        _make_package(root, "decoy", keywords="unrelated-topic")
        selected, warnings = routing.route_packages(
            "Let's dehydrate the mixture, please.", [], "", _context_paths(root), _resolver_paths(root)
        )
        self.assertEqual(selected, [])
        self.assertEqual(warnings, [])

    def test_implicit_selection_is_capped_and_ranked_at_scale(self):
        # Plan 2.1: the compile-context loading path was uncapped, unlike
        # `route_prompt_package_pointers`'s display path -- F15's fix was
        # applied to the wrong path. Package `i` has a keyword list diluted
        # with `i` non-matching fillers, so scores (1/(1+i)) are distinct and
        # the cap outcome is deterministic, not an ambiguity case.
        root = Path(tempfile.mkdtemp(prefix="routing-test-"))
        for i in range(20):
            fillers = "".join(f"\n  - filler{i}-{j}" for j in range(i))
            _make_package(root, f"pkg{i:02d}", keywords=f"\n  - engine{fillers}")
        selected, warnings = routing.route_packages(
            "Please do an engine refactor", [], "", _context_paths(root), _resolver_paths(root)
        )
        self.assertEqual(len(selected), routing.MAX_ROUTED_PACKAGES)
        self.assertEqual([item["package"] for item in selected], ["pkg00", "pkg01", "pkg02"])
        self.assertTrue(any("17 additional matching package(s) omitted" in w for w in warnings))

    def test_implicit_selection_rejects_ambiguous_cap_boundary(self):
        root = Path(tempfile.mkdtemp(prefix="routing-test-"))
        _make_package(root, "champion", keywords="\n  - engine\n  - refactor\n  - migrate")
        _make_package(root, "rival-a", keywords="\n  - engine\n  - launch")
        _make_package(root, "rival-b", keywords="\n  - engine\n  - deploy")
        _make_package(root, "rival-c", keywords="\n  - engine\n  - build")
        selected, warnings = routing.route_packages(
            "Please do an engine refactor", [], "", _context_paths(root), _resolver_paths(root)
        )
        self.assertEqual([item["package"] for item in selected], ["champion"])
        self.assertEqual(selected[0]["reason"], "routing keyword")
        ambiguity_warnings = [w for w in warnings if "ambiguous" in w]
        self.assertEqual(len(ambiguity_warnings), 1)
        for title in ("Rival-A", "Rival-B", "Rival-C"):
            self.assertIn(title, ambiguity_warnings[0])


class ValidateRoutingFileTests(unittest.TestCase):
    def test_reports_missing_required_fields(self):
        root = Path(tempfile.mkdtemp(prefix="routing-test-"))
        path = root / "routing.yaml"
        path.write_text(f"schema: {routing.ROUTING_SCHEMA}\n", encoding="utf-8")
        errors = routing.validate_routing_file(path, _context_paths(root), _resolver_paths(root))
        self.assertTrue(any("missing `package`" in error for error in errors))

    def test_reports_missing_state_target_alongside_missing_keywords(self):
        root = Path(tempfile.mkdtemp(prefix="routing-test-"))
        hydra_root = root / ".hydra-framework"
        path = hydra_root / "repo/knowledge/knowledge-packages/example/routing.yaml"
        path.parent.mkdir(parents=True)
        path.write_text(
            f"schema: {routing.ROUTING_SCHEMA}\n"
            "package: example\n"
            "title: Example\n"
            "state: .hydra-framework/repo/knowledge/knowledge-packages/example/missing.md\n",
            encoding="utf-8",
        )
        errors = [str(e) for e in routing.validate_routing_file(path, _context_paths(root), _resolver_paths(root))]
        rel = path.relative_to(root)
        self.assertIn(f"{rel} missing `keywords`", errors)
        self.assertIn(
            f"{rel} `state` target does not exist: "
            ".hydra-framework/repo/knowledge/knowledge-packages/example/missing.md",
            errors,
        )

    def _routing_with_route(
        self,
        root: Path,
        *,
        avoid_by_default: str = "",
        verify: str = "",
        priority_units: str = "",
        requires: str = "",
    ) -> Path:
        hydra_root = root / ".hydra-framework"
        pkg = hydra_root / "repo/knowledge/knowledge-packages/example"
        path = pkg / "routing.yaml"
        pkg.mkdir(parents=True)
        (pkg / "overview.md").write_text("# Overview\n", encoding="utf-8")
        body = (
            f"schema: {routing.ROUTING_SCHEMA}\n"
            "package: example\n"
            "title: Example\n"
            "keywords: alpha\n"
            "routes:\n"
            "  demo_route:\n"
            "    use_when:\n"
            "      - a task shape\n"
        )
        if avoid_by_default:
            body += f"    avoid_by_default:\n      - {avoid_by_default}\n"
        if verify:
            body += f"    verify:\n      - {verify}\n"
        if priority_units:
            body += f"    priority_units:\n      - {priority_units}\n"
        if requires:
            body += f"    requires:\n      - {requires}\n"
        path.write_text(body, encoding="utf-8")
        return path

    def test_avoid_by_default_path_that_does_not_exist_is_a_finding(self):
        root = Path(tempfile.mkdtemp(prefix="routing-test-"))
        (root / ".hydra-framework").mkdir()
        path = self._routing_with_route(root, avoid_by_default=".hydra-framework/nonexistent-subdir/")
        errors = [str(e) for e in routing.validate_routing_file(path, _context_paths(root), _resolver_paths(root))]
        self.assertTrue(any("avoid_by_default` path does not exist" in error for error in errors), errors)

    def test_avoid_by_default_prose_is_not_flagged(self):
        root = Path(tempfile.mkdtemp(prefix="routing-test-"))
        path = self._routing_with_route(root, avoid_by_default="the host repository's full source tree")
        errors = [str(e) for e in routing.validate_routing_file(path, _context_paths(root), _resolver_paths(root))]
        self.assertEqual(errors, [])

    def test_verify_command_not_in_command_ids_is_a_finding(self):
        root = Path(tempfile.mkdtemp(prefix="routing-test-"))
        path = self._routing_with_route(root, verify="python3 .hydra-framework/scripts/hydra.py totally-fake-command --wrong")
        errors = [str(e) for e in routing.validate_routing_file(
            path, _context_paths(root), _resolver_paths(root), command_ids=("validate", "export-adapters"),
        )]
        self.assertTrue(any("not a registered hydra.py command" in error for error in errors), errors)

    def test_verify_command_in_command_ids_passes(self):
        root = Path(tempfile.mkdtemp(prefix="routing-test-"))
        path = self._routing_with_route(root, verify="python3 .hydra-framework/scripts/hydra.py export-adapters --check")
        errors = [str(e) for e in routing.validate_routing_file(
            path, _context_paths(root), _resolver_paths(root), command_ids=("validate", "export-adapters"),
        )]
        self.assertEqual(errors, [])

    def test_verify_command_skipped_when_no_command_ids_given(self):
        root = Path(tempfile.mkdtemp(prefix="routing-test-"))
        path = self._routing_with_route(root, verify="python3 .hydra-framework/scripts/hydra.py totally-fake-command")
        errors = [str(e) for e in routing.validate_routing_file(path, _context_paths(root), _resolver_paths(root))]
        self.assertEqual(errors, [])

    def test_verify_command_with_binary_missing_from_path_is_a_finding(self):
        root = Path(tempfile.mkdtemp(prefix="routing-test-"))
        path = self._routing_with_route(root, verify="totally-nonexistent-binary-xyz --check")
        errors = [str(e) for e in routing.validate_routing_file(path, _context_paths(root), _resolver_paths(root))]
        self.assertTrue(any("command binary not found on PATH" in error for error in errors), errors)

    def test_verify_command_with_real_binary_passes(self):
        root = Path(tempfile.mkdtemp(prefix="routing-test-"))
        path = self._routing_with_route(root, verify="grep -rn foo .")
        errors = [str(e) for e in routing.validate_routing_file(path, _context_paths(root), _resolver_paths(root))]
        self.assertEqual(errors, [])

    def test_verify_command_with_shell_metacharacters_is_not_flagged(self):
        root = Path(tempfile.mkdtemp(prefix="routing-test-"))
        path = self._routing_with_route(root, verify="cd .. && totally-nonexistent-binary-xyz")
        errors = [str(e) for e in routing.validate_routing_file(path, _context_paths(root), _resolver_paths(root))]
        self.assertEqual(errors, [])

    def test_priority_unit_id_that_does_not_resolve_is_a_finding(self):
        root = Path(tempfile.mkdtemp(prefix="routing-test-"))
        path = self._routing_with_route(root, priority_units="hydra://knowledge-unit/example/missing")
        errors = [str(e) for e in routing.validate_routing_file(path, _context_paths(root), _resolver_paths(root))]
        self.assertTrue(any("priority_units` id does not resolve" in error for error in errors), errors)

    def test_requires_unit_id_that_does_not_resolve_is_a_finding(self):
        root = Path(tempfile.mkdtemp(prefix="routing-test-"))
        path = self._routing_with_route(root, requires="hydra://knowledge-unit/example/missing")
        errors = [str(e) for e in routing.validate_routing_file(path, _context_paths(root), _resolver_paths(root))]
        self.assertTrue(any("requires` id does not resolve" in error for error in errors), errors)


class ContextTermsTests(unittest.TestCase):
    def test_stopwords_are_excluded(self):
        self.assertNotIn("the", routing.context_terms("fix the flaky login test"))

    def test_meaningful_terms_survive(self):
        terms = routing.context_terms("fix the flaky login test")
        self.assertIn("fix", terms)
        self.assertIn("flaky", terms)
        self.assertIn("login", terms)

    def test_stopword_overlap_no_longer_scores_a_route_match(self):
        # F15's exact repro: a task and a route's `use_when` sharing only
        # "fix" and "the" must no longer clear MIN_ROUTE_MATCH_SCORE.
        routing_data = {
            "routes": {
                "fix_provider_surface": {
                    "use_when": ["reclaim or the post-edit hook reports an orphaned drifted or stale provider file"],
                },
            },
        }
        route = routing.select_route(routing_data, "fix the flaky login test in the payments service")
        self.assertIsNone(route)


class RoutePromptPackagePointersTests(unittest.TestCase):
    def test_matches_by_keyword_and_carries_the_note_through(self):
        root = Path(tempfile.mkdtemp(prefix="routing-test-"))
        _make_package(root, "example", keywords="\n  - engine refactor")
        matches, warnings = routing.route_prompt_package_pointers(
            "Please do an engine refactor", _context_paths(root), _resolver_paths(root)
        )
        self.assertEqual(warnings, [])
        self.assertEqual(len(matches), 1)
        self.assertEqual(matches[0].title, "Example")

    def test_schema_mismatch_is_a_warning_not_a_match(self):
        root = Path(tempfile.mkdtemp(prefix="routing-test-"))
        pkg = root / ".hydra-framework/repo/knowledge/knowledge-packages/wrong"
        pkg.mkdir(parents=True)
        (pkg / "overview.md").write_text("# Overview\n", encoding="utf-8")
        (pkg / "routing.yaml").write_text(
            "schema: wrong.schema.v1\npackage: wrong\ntitle: Wrong Package\nkeywords:\n  - engine refactor\n",
            encoding="utf-8",
        )
        matches, warnings = routing.route_prompt_package_pointers(
            "Please do an engine refactor", _context_paths(root), _resolver_paths(root)
        )
        self.assertEqual(matches, [])
        self.assertTrue(any("schema is not" in warning for warning in warnings))

    def test_no_keyword_hit_with_one_package_stays_empty(self):
        root = Path(tempfile.mkdtemp(prefix="routing-test-"))
        _make_package(root, "example", keywords="\n  - unrelated-topic")
        matches, warnings = routing.route_prompt_package_pointers(
            "Please do an engine refactor", _context_paths(root), _resolver_paths(root)
        )
        self.assertEqual(matches, [])
        self.assertEqual(warnings, [])

    def test_no_keyword_hit_with_multiple_packages_stays_empty(self):
        root = Path(tempfile.mkdtemp(prefix="routing-test-"))
        _make_package(root, "first", keywords="\n  - unrelated-topic")
        _make_package(root, "second", keywords="\n  - different-topic")
        matches, warnings = routing.route_prompt_package_pointers(
            "Please do an engine refactor", _context_paths(root), _resolver_paths(root)
        )
        self.assertEqual(matches, [])
        self.assertEqual(warnings, [])

    def test_matches_are_capped_and_ranked_by_keyword_score(self):
        # F15: an uncapped, unranked match set scales with package count.
        # Each package's score is the proportion of its own `keywords:` that
        # match, so distinct rankings need distinct match proportions, not
        # just distinct match counts (a package can't buy priority by only
        # padding its keyword list -- see `_package_keyword_score`).
        root = Path(tempfile.mkdtemp(prefix="routing-test-"))
        _make_package(root, "solid", keywords="\n  - engine\n  - refactor")
        _make_package(root, "partial", keywords="\n  - engine\n  - refactor\n  - launch")
        _make_package(root, "faint", keywords="\n  - engine\n  - launch")
        _make_package(root, "bare", keywords="\n  - engine\n  - launch\n  - deploy")
        matches, warnings = routing.route_prompt_package_pointers(
            "Please do an engine refactor", _context_paths(root), _resolver_paths(root)
        )
        self.assertEqual(len(matches), routing.MAX_ROUTED_PACKAGES)
        self.assertEqual(matches[0].title, "Solid")
        self.assertTrue(any("additional matching package(s) omitted" in w for w in warnings))

    def test_configured_cap_changes_implicit_package_limit(self):
        root = Path(tempfile.mkdtemp(prefix="routing-test-"))
        _make_package(root, "first", keywords="\n  - engine\n  - unrelated-filler")
        _make_package(root, "second", keywords="engine")
        matches, warnings = routing.route_prompt_package_pointers(
            "Please do engine work", _context_paths(root), _resolver_paths(root), max_routed_packages=1,
        )
        self.assertEqual(len(matches), 1)
        self.assertEqual(matches[0].title, "Second")
        self.assertTrue(any("showing the top 1" in warning for warning in warnings))

    def test_ambiguous_cap_boundary_is_rejected_not_spelling_ordered(self):
        # The normalized scorer makes ties a real, expected outcome (three
        # packages that each fully satisfy a one-word keyword list score
        # identically) rather than the F15-era edge case they used to be;
        # this is the direct regression test for "reject ambiguous ...
        # ties instead of breaking ties by spelling."
        root = Path(tempfile.mkdtemp(prefix="routing-test-"))
        _make_package(root, "champion", keywords="\n  - engine\n  - refactor\n  - migrate")
        _make_package(root, "rival-a", keywords="\n  - engine\n  - launch")
        _make_package(root, "rival-b", keywords="\n  - engine\n  - deploy")
        _make_package(root, "rival-c", keywords="\n  - engine\n  - build")
        matches, warnings = routing.route_prompt_package_pointers(
            "Please do an engine refactor", _context_paths(root), _resolver_paths(root)
        )
        self.assertEqual([match.title for match in matches], ["Champion"])
        self.assertFalse(any("additional matching package(s) omitted" in w for w in warnings))
        ambiguity_warnings = [w for w in warnings if "ambiguous" in w]
        self.assertEqual(len(ambiguity_warnings), 1)
        for title in ("Rival-A", "Rival-B", "Rival-C"):
            self.assertIn(title, ambiguity_warnings[0])

    def test_full_tie_at_cap_rejects_all_rather_than_choosing_by_spelling(self):
        root = Path(tempfile.mkdtemp(prefix="routing-test-"))
        for name in ["alpha", "bravo", "charlie", "delta"]:
            _make_package(root, name, keywords="engine")
        matches, warnings = routing.route_prompt_package_pointers(
            "Please do an engine refactor", _context_paths(root), _resolver_paths(root)
        )
        self.assertEqual(matches, [])
        self.assertTrue(any("ambiguous" in w for w in warnings))

    def test_explicit_package_request_is_never_capped(self):
        root = Path(tempfile.mkdtemp(prefix="routing-test-"))
        for name in ["one", "two", "three", "four"]:
            _make_package(root, name, keywords="alpha")
        matches, warnings = routing.route_prompt_package_pointers(
            "prompt", _context_paths(root), _resolver_paths(root), tuple(["one", "two", "three", "four"]),
        )
        self.assertEqual(len(matches), 4)
        self.assertEqual(warnings, [])

    def test_route_name_discussion_does_not_activate_route_pointer_semantics(self):
        root = Path(tempfile.mkdtemp(prefix="routing-test-"))
        pkg = root / ".hydra-framework/repo/knowledge/knowledge-packages/example"
        (pkg / "units").mkdir(parents=True)
        (pkg / "overview.md").write_text("# Overview\n", encoding="utf-8")
        (pkg / "routing.yaml").write_text(
            f"schema: {routing.ROUTING_SCHEMA}\n"
            "package: example\n"
            "title: Example\n"
            "keywords:\n"
            "  - hydra\n"
            "routes:\n"
            "  adopt_into_repo:\n"
            "    use_when:\n"
            "      - Hydra was copied into a repository and needs wiring\n"
            "    priority_units:\n"
            "      - hydra://knowledge-unit/example/adopt\n"
            "    avoid_by_default:\n"
            "      - the host repository's full source tree\n",
            encoding="utf-8",
        )
        matches, warnings = routing.route_prompt_package_pointers(
            "Explain the adopt_into_repo route; do not adopt Hydra here.",
            _context_paths(root),
            _resolver_paths(root),
            ("example",),
        )
        self.assertEqual(warnings, [])
        self.assertEqual(len(matches), 1)
        self.assertEqual(matches[0].route, "")
        self.assertEqual(matches[0].priority_units, ())
        self.assertEqual(matches[0].avoid_by_default, ())


if __name__ == "__main__":
    unittest.main()
