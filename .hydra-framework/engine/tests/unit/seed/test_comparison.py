"""Mirror test for `hydra_engine.seed.comparison`.

Split from `test_hydra.py`'s `SeedComparisonTests`, which had no live-repo
dependency for these cases (only its hashing tests did, moved to
`test_fingerprints.py`).
"""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

_SRC = Path(__file__).resolve().parents[3] / "src"
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

from hydra_engine.seed import comparison  # noqa: E402
from hydra_engine.seed.adaptations import parse_adaptation_ledger_text  # noqa: E402


class SchemaDriftReasonTests(unittest.TestCase):
    def test_returns_the_reason_when_present(self):
        drift = {"repo/knowledge-units/0001-test.md": "schema_version 1 behind base (2)"}
        self.assertEqual(
            comparison.schema_drift_reason("repo/knowledge-units/0001-test.md", drift),
            ["schema_version 1 behind base (2)"],
        )

    def test_returns_empty_when_absent(self):
        self.assertEqual(comparison.schema_drift_reason("repo/knowledge-units/0001-test.md", {}), [])


class SplitDifferencesByAdaptationTests(unittest.TestCase):
    def test_diff_split_uses_adaptation_ledger_paths(self):
        rows = {
            "local-modified": ["scripts/hydra.py"],
            "local-only": ["repo/knowledge/project.md"],
            "base-only": [],
        }
        entries = parse_adaptation_ledger_text(
            "## 2026-07-30 - script-change\n\n"
            "Base seed version: 0.1.0\n"
            "Disposition: promote-candidate\n"
            "Paths touched:\n"
            "- .hydra-framework/scripts/hydra.py\n"
            "Why:\n"
            "- Behavior changed deliberately.\n"
            "Evidence:\n"
            "- Covered by tests.\n"
        )
        split = comparison.split_differences_by_adaptation(rows, entries)
        self.assertEqual([item["path"] for item in split["explained"]], ["scripts/hydra.py"])
        self.assertEqual(split["explained"][0]["explained_by"], ["2026-07-30 - script-change"])
        self.assertEqual([item["path"] for item in split["unexplained"]], ["repo/knowledge/project.md"])

    def test_adoption_side_effects_are_not_reported_as_drift(self):
        """Every adopted copy rewrites these two; requiring a ledger entry for them
        would make `--fail-on-drift` permanently unpassable."""
        rows = {
            "local-modified": ["manifest.yaml", "evolution/adaptations.md"],
            "local-only": [],
            "base-only": [],
        }
        split = comparison.split_differences_by_adaptation(rows, [])
        self.assertEqual(split["unexplained"], [])
        self.assertEqual(len(split["explained"]), 2)
        for item in split["explained"]:
            self.assertTrue(item["explained_by"][0].startswith("expected:"))

    def test_schema_version_drift_is_explained_not_unexplained(self):
        """Gap 1: being behind on schema_version is a known, actionable state,
        not indistinguishable from deliberate unexplained drift."""
        rows = {
            "local-modified": ["repo/knowledge-units/0001-test.md"],
            "local-only": [],
            "base-only": [],
        }
        drift = {"repo/knowledge-units/0001-test.md": "schema_version 1 behind base (2); run `hydra.py schema upgrade`"}
        split = comparison.split_differences_by_adaptation(rows, [], drift)
        self.assertEqual(split["unexplained"], [])
        self.assertEqual(split["explained"][0]["explained_by"], [drift["repo/knowledge-units/0001-test.md"]])

    def test_ledger_explanation_takes_precedence_over_schema_drift(self):
        rows = {"local-modified": ["repo/knowledge-units/0001-test.md"], "local-only": [], "base-only": []}
        entries = parse_adaptation_ledger_text(
            "## 2026-07-30 - deliberate-change\n\n"
            "Base seed version: 0.1.0\n"
            "Disposition: repo-local\n"
            "Paths touched:\n"
            "- .hydra-framework/repo/knowledge-units/0001-test.md\n"
            "Why:\n"
            "- Repository-specific.\n"
            "Evidence:\n"
            "- Reviewed.\n"
        )
        drift = {"repo/knowledge-units/0001-test.md": "schema_version 1 behind base (2); run `hydra.py schema upgrade`"}
        split = comparison.split_differences_by_adaptation(rows, entries, drift)
        self.assertEqual(split["explained"][0]["explained_by"], ["2026-07-30 - deliberate-change"])

    def test_unexplained_when_nothing_accounts_for_it(self):
        rows = {"local-modified": [], "local-only": ["repo/knowledge/new.md"], "base-only": []}
        split = comparison.split_differences_by_adaptation(rows, [])
        self.assertEqual([item["path"] for item in split["unexplained"]], ["repo/knowledge/new.md"])
        self.assertEqual(split["explained"], [])


if __name__ == "__main__":
    unittest.main()
