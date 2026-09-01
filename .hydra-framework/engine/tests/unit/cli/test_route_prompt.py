"""Mirror test for `hydra_engine.cli.route_prompt`."""

from __future__ import annotations

import contextlib
import io
import json
import sys
import tempfile
import unittest
from pathlib import Path

_SRC = Path(__file__).resolve().parents[3] / "src"
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

from hydra_engine import thresholds  # noqa: E402
from hydra_engine.cli import route_prompt  # noqa: E402
from hydra_engine.cli.dispatch import RepoContext  # noqa: E402


def _ctx() -> RepoContext:
    root = Path(tempfile.mkdtemp(prefix="route-prompt-test-"))
    (root / ".hydra-framework").mkdir(parents=True)
    return RepoContext.for_root(root)


def _seed_package(ctx: RepoContext) -> None:
    pkg = ctx.hydra / "repo/knowledge/knowledge-packages/example"
    pkg.mkdir(parents=True)
    (pkg / "state.md").write_text("# State\n", encoding="utf-8")
    (pkg / "overview.md").write_text("# Overview\n", encoding="utf-8")
    (pkg / "routing.yaml").write_text(
        "schema: hydra-framework.package-routing.v2\n"
        "package: example\n"
        "title: Example Package\n"
        "keywords:\n  - engine refactor\n"
        "state: .hydra-framework/repo/knowledge/knowledge-packages/example/state.md\n"
        "note: Keep scope narrow.\n",
        encoding="utf-8",
    )


def _write_config(ctx: RepoContext, **overrides: int) -> None:
    config_dir = ctx.hydra / "config"
    config_dir.mkdir(parents=True)
    lines = ["schema: hydra-framework.engine-policy.v1", "thresholds:"]
    for entry in thresholds.THRESHOLDS:
        if entry.classification == thresholds.TEAM_TUNABLE_POLICY:
            lines.append(f"  {entry.key}: {overrides.get(entry.key, entry.value)}")
    (config_dir / "engine-policy.yaml").write_text("\n".join(lines) + "\n", encoding="utf-8")
    (config_dir / "delegation-policy.yaml").write_text(
        "schema: hydra-framework.delegation-policy.v1\n"
        "enabled: true\nmax_active_workers: 2\nmax_depth: 1\n"
        "allowed_reasons:\n  - inspection\n"
        "role_defaults:\n  allowed_capability_classes:\n    - fast-default\n"
        "  fallback_capability_class: fast-default\n  effort_ceiling: max\n"
        "roles: {}\n",
        encoding="utf-8",
    )


def _seed_wrong_schema_package(ctx: RepoContext) -> None:
    pkg = ctx.hydra / "repo/knowledge/knowledge-packages/wrong"
    pkg.mkdir(parents=True)
    (pkg / "routing.yaml").write_text(
        "schema: wrong.schema.v1\npackage: wrong\ntitle: Wrong Package\nkeywords:\n  - engine refactor\n",
        encoding="utf-8",
    )


def _seed_package_with_route(ctx: RepoContext) -> None:
    pkg = ctx.hydra / "repo/knowledge/knowledge-packages/example"
    units = pkg / "units"
    units.mkdir(parents=True)
    (pkg / "state.md").write_text("# State\n", encoding="utf-8")
    (pkg / "overview.md").write_text("# Overview\n", encoding="utf-8")
    (units / "adopt.md").write_text(
        "---\nhydra_id: hydra://knowledge-unit/example/adopt\nuid: 11111111-1111-4111-8111-111111111111\n"
        "schema_version: 3\nkind: knowledge-unit\nunit_kind: answer\ntitle: Adopt\nstatus: active\nscope: repo\n"
        "owners:\n  team: fixture\nrelations: []\nprovenance:\n  sources: []\nquestion: How is Hydra adopted?\n"
        "---\n# Adopt\n",
        encoding="utf-8",
    )
    (pkg / "routing.yaml").write_text(
        "schema: hydra-framework.package-routing.v2\n"
        "package: example\n"
        "title: Example Package\n"
        "keywords:\n  - engine refactor\n"
        "state: .hydra-framework/repo/knowledge/knowledge-packages/example/state.md\n"
        "note: Keep scope narrow.\n"
        "routes:\n"
        "  adopt_into_repo:\n"
        "    use_when:\n"
        "      - engine refactor adoption\n"
        "    priority_units:\n"
        "      - hydra://knowledge-unit/example/adopt\n"
        "    avoid_by_default:\n"
        "      - generated/**\n",
        encoding="utf-8",
    )


class CommandRoutePromptTests(unittest.TestCase):
    def test_matching_prompt_prints_pointers(self):
        ctx = _ctx()
        _seed_package(ctx)
        out = io.StringIO()
        args = type("Args", (), {"prompt": "Please do an engine refactor"})()
        with contextlib.redirect_stdout(out):
            self.assertEqual(route_prompt.command_route_prompt(args, ctx), 0)
        self.assertIn("Hydra package routing (pointers only):", out.getvalue())
        self.assertIn("Example Package", out.getvalue())

    def test_configured_package_cap_limits_implicit_matches(self):
        ctx = _ctx()
        _write_config(ctx, **{"hydra_engine.knowledge.routing.MAX_ROUTED_PACKAGES": 1})
        _seed_package(ctx)
        other = ctx.hydra / "repo/knowledge/knowledge-packages/other"
        other.mkdir(parents=True)
        (other / "state.md").write_text("# State\n", encoding="utf-8")
        (other / "overview.md").write_text("# Overview\n", encoding="utf-8")
        (other / "routing.yaml").write_text(
            "schema: hydra-framework.package-routing.v2\n"
            "package: other\n"
            "title: Other Package\n"
            # A second, non-matching keyword dilutes this package's score
            # below `example`'s so the single cap slot has a clear winner,
            # not a tie (a tied cutoff is ambiguous and drops both).
            "keywords:\n  - engine refactor\n  - unrelated-filler\n",
            encoding="utf-8",
        )
        out, err = io.StringIO(), io.StringIO()
        args = type("Args", (), {"prompt": "Please do an engine refactor"})()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            self.assertEqual(route_prompt.command_route_prompt(args, ctx), 0)
        self.assertEqual(out.getvalue().count("Package"), 1)
        self.assertIn("showing the top 1", err.getvalue())

    def test_broken_routing_file_reports_a_warning_alongside_the_matches(self):
        ctx = _ctx()
        _seed_package(ctx)
        _seed_wrong_schema_package(ctx)
        out, err = io.StringIO(), io.StringIO()
        args = type("Args", (), {"prompt": "Please do an engine refactor"})()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            self.assertEqual(route_prompt.command_route_prompt(args, ctx), 0)
        self.assertIn("Example Package", out.getvalue())
        self.assertIn(
            "Hydra routing skipped: .hydra-framework/repo/knowledge/knowledge-packages/wrong/routing.yaml "
            "schema is not `hydra-framework.package-routing.v2`",
            err.getvalue(),
        )

    def test_stdin_json_input_is_read_when_prompt_argument_is_empty(self):
        ctx = _ctx()
        _seed_package(ctx)
        args = type("Args", (), {"prompt": ""})()
        saved_stdin = sys.stdin
        sys.stdin = io.StringIO(json.dumps({"prompt": "engine refactor from hook"}))
        self.addCleanup(lambda: setattr(sys, "stdin", saved_stdin))
        out = io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(io.StringIO()):
            self.assertEqual(route_prompt.command_route_prompt(args, ctx), 0)
        self.assertIn("Hydra package routing (pointers only):", out.getvalue())
        self.assertIn("Example Package", out.getvalue())

    def test_route_prompt_output_does_not_render_route_directives(self):
        ctx = _ctx()
        _seed_package_with_route(ctx)
        out = io.StringIO()
        args = type("Args", (), {"prompt": "Please do an engine refactor adoption"})()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(io.StringIO()):
            self.assertEqual(route_prompt.command_route_prompt(args, ctx), 0)
        output = out.getvalue()
        self.assertIn("Hydra package routing (pointers only):", output)
        self.assertIn("Example Package", output)
        self.assertNotIn("Route:", output)
        self.assertNotIn("hydra://knowledge-unit/example/adopt", output)
        self.assertNotIn("Avoid by default:", output)
        self.assertNotIn("generated/**", output)

    def test_route_prompt_renders_exact_path_references_without_a_package_match(self):
        ctx = _ctx()
        note = ctx.hydra / "repo/knowledge/routing-note.md"
        note.parent.mkdir(parents=True, exist_ok=True)
        note.write_text("# Routing Note\n", encoding="utf-8")
        out = io.StringIO()
        args = type("Args", (), {"prompt": "Read .hydra-framework/repo/knowledge/routing-note.md"})()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(io.StringIO()):
            self.assertEqual(route_prompt.command_route_prompt(args, ctx), 0)
        output = out.getvalue()
        self.assertIn("Hydra exact references:", output)
        self.assertIn("`.hydra-framework/repo/knowledge/routing-note.md`", output)
        self.assertNotIn("Hydra package routing (pointers only):", output)

    def test_second_turn_with_same_session_and_same_output_emits_nothing(self):
        ctx = _ctx()
        _seed_package(ctx)
        args = type("Args", (), {"prompt": ""})()
        payload = json.dumps({"prompt": "engine refactor from hook", "session_id": "session-123"})

        saved_stdin = sys.stdin
        sys.stdin = io.StringIO(payload)
        self.addCleanup(lambda: setattr(sys, "stdin", saved_stdin))
        first = io.StringIO()
        with contextlib.redirect_stdout(first), contextlib.redirect_stderr(io.StringIO()):
            self.assertEqual(route_prompt.command_route_prompt(args, ctx), 0)

        sys.stdin = io.StringIO(payload)
        second = io.StringIO()
        with contextlib.redirect_stdout(second), contextlib.redirect_stderr(io.StringIO()):
            self.assertEqual(route_prompt.command_route_prompt(args, ctx), 0)

        self.assertIn("Hydra package routing (pointers only):", first.getvalue())
        self.assertEqual(second.getvalue(), "")

    def test_empty_prompt_prints_nothing(self):
        ctx = _ctx()
        args = type("Args", (), {"prompt": ""})()
        saved_stdin = sys.stdin
        sys.stdin = io.StringIO("")
        self.addCleanup(lambda: setattr(sys, "stdin", saved_stdin))
        out, err = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            self.assertEqual(route_prompt.command_route_prompt(args, ctx), 0)
        self.assertEqual(out.getvalue(), "")
        self.assertEqual(err.getvalue(), "")

    def test_json_diagnostic_output_carries_score_reason_references_and_timing(self):
        ctx = _ctx()
        _seed_package(ctx)
        note = ctx.hydra / "repo/knowledge/routing-note.md"
        note.parent.mkdir(parents=True, exist_ok=True)
        note.write_text("# Routing Note\n", encoding="utf-8")
        out = io.StringIO()
        args = type("Args", (), {
            "prompt": "Please do an engine refactor; read .hydra-framework/repo/knowledge/routing-note.md",
            "json": True,
        })()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(io.StringIO()):
            self.assertEqual(route_prompt.command_route_prompt(args, ctx), 0)
        diagnostics = json.loads(out.getvalue())
        self.assertEqual(len(diagnostics["matches"]), 1)
        self.assertEqual(diagnostics["matches"][0]["package"], "example")
        self.assertEqual(diagnostics["matches"][0]["reason"], "routing keyword")
        self.assertGreater(diagnostics["matches"][0]["score"], 0)
        self.assertEqual(len(diagnostics["exact_references"]), 1)
        self.assertIn(".hydra-framework/repo/knowledge/routing-note.md", diagnostics["exact_references"][0]["path"])
        self.assertFalse(diagnostics["suppressed"])
        self.assertGreaterEqual(diagnostics["timing_ms"], 0)

    def test_json_diagnostic_does_not_advance_session_suppression_state(self):
        ctx = _ctx()
        _seed_package(ctx)
        payload = json.dumps({"prompt": "engine refactor from hook", "session_id": "session-json"})

        saved_stdin = sys.stdin
        self.addCleanup(lambda: setattr(sys, "stdin", saved_stdin))

        sys.stdin = io.StringIO(payload)
        json_out = io.StringIO()
        with contextlib.redirect_stdout(json_out), contextlib.redirect_stderr(io.StringIO()):
            args = type("Args", (), {"prompt": "", "json": True})()
            self.assertEqual(route_prompt.command_route_prompt(args, ctx), 0)
        self.assertFalse(json.loads(json_out.getvalue())["suppressed"])

        sys.stdin = io.StringIO(payload)
        text_out = io.StringIO()
        with contextlib.redirect_stdout(text_out), contextlib.redirect_stderr(io.StringIO()):
            args = type("Args", (), {"prompt": ""})()
            self.assertEqual(route_prompt.command_route_prompt(args, ctx), 0)
        self.assertIn("Hydra package routing (pointers only):", text_out.getvalue())


if __name__ == "__main__":
    unittest.main()
