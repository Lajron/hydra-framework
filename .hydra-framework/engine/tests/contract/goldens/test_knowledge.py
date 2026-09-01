"""knowledge goldens: measure-context,
validate-package-docs, compile-context, route-prompt."""

from __future__ import annotations

import unittest

from .fixtures import assert_golden, run_golden


class KnowledgeGoldenTests(unittest.TestCase):
    def test_measure_context_happy_path(self):
        outcome = run_golden(["measure-context"])
        assert_golden(self, "knowledge-measure-context", outcome)

    def test_measure_context_json(self):
        outcome = run_golden(["measure-context", "--json"])
        assert_golden(self, "knowledge-measure-context-json", outcome)

    def test_measure_context_fail_over_exceeded(self):
        outcome = run_golden(["measure-context", "--fail-over", "1"])
        assert_golden(self, "knowledge-measure-context-fail-over", outcome)

    def test_validate_package_docs_happy_path(self):
        """No knowledge packages present: still a real happy path
        (`no knowledge packages found`)."""
        outcome = run_golden(["validate-package-docs"])
        assert_golden(self, "knowledge-validate-package-docs", outcome)

    def test_validate_package_docs_broken_link(self):
        outcome = run_golden(
            ["validate-package-docs"],
            extra_fixture={
                ".hydra-framework/repo/knowledge/knowledge-packages/demo/overview.md": "[broken](missing.md)\n",
            },
        )
        assert_golden(self, "knowledge-validate-package-docs-broken-link", outcome)

    def test_validate_package_docs_broken_routing(self):
        outcome = run_golden(
            ["validate-package-docs"],
            extra_fixture={
                ".hydra-framework/repo/knowledge/knowledge-packages/demo/routing.yaml": (
                    "schema: hydra-framework.package-routing.v2\npackage: demo\ntitle: Demo\n"
                ),
            },
        )
        assert_golden(self, "knowledge-validate-package-docs-broken-routing", outcome)

    def test_validate_package_docs_render_flag_with_no_diagrams(self):
        """`--render` on a package with no `diagrams/*.dot` files: the render
        path returns immediately without touching the `dot` binary, so this
        stays deterministic on a machine without Graphviz installed."""
        outcome = run_golden(
            ["validate-package-docs", "--render"],
            extra_fixture={
                ".hydra-framework/repo/knowledge/knowledge-packages/demo/overview.md": "# Demo\n",
            },
        )
        assert_golden(self, "knowledge-validate-package-docs-render-no-diagrams", outcome)

    def test_compile_context_happy_path(self):
        outcome = run_golden(["compile-context", "--task", "fixture task"])
        assert_golden(self, "knowledge-compile-context", outcome)

    def test_compile_context_refusal_missing_task(self):
        """Closed once `command_compile_context` moved into the engine."""
        outcome = run_golden(["compile-context"], stdin="")
        assert_golden(self, "knowledge-compile-context-refusal-missing-task", outcome)

    def test_route_prompt_happy_path(self):
        outcome = run_golden(["route-prompt", "--prompt", "fixture prompt"])
        assert_golden(self, "knowledge-route-prompt", outcome)


if __name__ == "__main__":
    unittest.main()
