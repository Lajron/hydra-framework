"""seed goldens: diff-base, evolution record."""

from __future__ import annotations

import unittest

from .fixtures import BASE_FIXTURE, assert_golden, external_dir, run_golden


class SeedGoldenTests(unittest.TestCase):
    def test_diff_base_happy_path(self):
        """Base and local are byte-identical: zero unexplained differences.
        Real drift/explained-by-ledger classification is covered at the unit
        level in `tests/unit/seed/test_comparison.py`."""
        base_fixture = {rel: content for rel, content in BASE_FIXTURE.items() if rel.startswith(".hydra-framework/")}
        with external_dir(base_fixture) as base_root:
            base_hydra = base_root / ".hydra-framework"
            outcome = run_golden(["diff-base", "--base", str(base_hydra)])
            assert_golden(self, "seed-diff-base", outcome, stdout_replacements={str(base_hydra): "<BASE_HYDRA>"})

    def test_evolution_record_happy_path(self):
        outcome = run_golden(
            [
                "evolution",
                "record",
                "--title",
                "Fixture entry",
                "--disposition",
                "repo-local",
                "--path",
                "scripts/hydra.py",
                "--why",
                "fixture reason",
                "--evidence",
                "fixture evidence",
            ]
        )
        assert_golden(self, "seed-evolution-record", outcome)

    def test_diff_base_unexplained_difference_with_fail_on_drift(self):
        """A local-only file with no
        ledger entry is unexplained, and `--fail-on-drift` exits 2."""
        extra_fixture = {".hydra-framework/repo/knowledge/example.md": "# Example\n\nNew content.\n"}
        base_fixture = {rel: content for rel, content in BASE_FIXTURE.items() if rel.startswith(".hydra-framework/")}
        with external_dir(base_fixture) as base_root:
            base_hydra = base_root / ".hydra-framework"
            outcome = run_golden(
                ["diff-base", "--base", str(base_hydra), "--fail-on-drift"],
                extra_fixture=extra_fixture,
            )
            assert_golden(
                self,
                "seed-diff-base-unexplained-fail-on-drift",
                outcome,
                stdout_replacements={str(base_hydra): "<BASE_HYDRA>"},
            )

    def test_diff_base_explained_by_ledger(self):
        """A modified file with a matching adaptation-ledger entry is
        explained, not unexplained."""
        ledger_text = (
            "## 2026-01-01 - example-change\n\n"
            "Base seed version: 0.1.0\n"
            "Disposition: repo-local\n"
            "Paths touched:\n"
            "- repo/knowledge/example.md\n"
            "Why:\n"
            "- Repository-specific customization.\n"
            "Evidence:\n"
            "- Reviewed manually.\n"
        )
        extra_fixture = {
            ".hydra-framework/repo/knowledge/example.md": "# Example\n\nModified.\n",
            ".hydra-framework/evolution/adaptations.md": ledger_text,
        }
        base_fixture = {rel: content for rel, content in BASE_FIXTURE.items() if rel.startswith(".hydra-framework/")}
        base_fixture[".hydra-framework/repo/knowledge/example.md"] = "# Example\n\nOriginal.\n"
        with external_dir(base_fixture) as base_root:
            base_hydra = base_root / ".hydra-framework"
            outcome = run_golden(["diff-base", "--base", str(base_hydra)], extra_fixture=extra_fixture)
            assert_golden(
                self,
                "seed-diff-base-explained-by-ledger",
                outcome,
                stdout_replacements={str(base_hydra): "<BASE_HYDRA>"},
            )

    def test_diff_base_json_output(self):
        base_fixture = {rel: content for rel, content in BASE_FIXTURE.items() if rel.startswith(".hydra-framework/")}
        with external_dir(base_fixture) as base_root:
            base_hydra = base_root / ".hydra-framework"
            outcome = run_golden(["diff-base", "--base", str(base_hydra), "--json"])
            assert_golden(
                self, "seed-diff-base-json", outcome, stdout_replacements={str(base_hydra): "<BASE_HYDRA>"}
            )

    def test_evolution_record_invalid_date_refuses(self):
        outcome = run_golden(
            [
                "evolution",
                "record",
                "--title",
                "Fixture entry",
                "--date",
                "2026-13-01",
                "--disposition",
                "repo-local",
                "--path",
                "scripts/hydra.py",
                "--why",
                "fixture reason",
                "--evidence",
                "fixture evidence",
            ]
        )
        assert_golden(self, "seed-evolution-record-invalid-date", outcome)


if __name__ == "__main__":
    unittest.main()
