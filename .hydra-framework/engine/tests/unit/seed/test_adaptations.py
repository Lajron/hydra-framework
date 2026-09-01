"""Mirror test for `hydra_engine.seed.adaptations`.

`parse_adaptation_ledger_text`/`validate_adaptation_entries`/
`validate_adaptations_ledger`/`append_adaptation_entry` split from
`test_hydra.py`'s `EvolutionRecordTests`, which monkeypatched
`hydra.ADAPTATION_LEDGER` to a tmp path; converted to passing the tmp path
directly, since these functions now take it as an explicit parameter rather
than reading a module global. `normalize_adaptation_path`,
`ledger_entries_for_path`, `format_adaptation_entry`, and
`current_base_seed_version` had no prior coverage and are newly tested here.
"""

from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

_SRC = Path(__file__).resolve().parents[3] / "src"
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

from hydra_engine.seed import adaptations  # noqa: E402


def _ledger_path() -> Path:
    return Path(tempfile.mkdtemp(prefix="seed-adaptations-")) / "adaptations.md"


class NormalizeAdaptationPathTests(unittest.TestCase):
    def test_strips_framework_prefix(self):
        self.assertEqual(
            adaptations.normalize_adaptation_path(".hydra-framework/scripts/hydra.py"),
            "scripts/hydra.py",
        )

    def test_leaves_already_relative_paths_alone(self):
        self.assertEqual(adaptations.normalize_adaptation_path("repo/knowledge/example.md"), "repo/knowledge/example.md")

    def test_strips_surrounding_whitespace(self):
        self.assertEqual(adaptations.normalize_adaptation_path("  repo/knowledge/example.md  "), "repo/knowledge/example.md")


class ParseAdaptationLedgerTextTests(unittest.TestCase):
    def test_parses_a_well_formed_entry(self):
        text = (
            "## 2026-07-30 - example\n\n"
            "Base seed version: 0.1.0\n"
            "Disposition: repo-local\n"
            "Paths touched:\n"
            "- repo/knowledge/example.md\n"
            "Why:\n"
            "- Needed by this repository.\n"
            "Evidence:\n"
            "- Checked by selftest.\n"
        )
        entries = adaptations.parse_adaptation_ledger_text(text)
        self.assertEqual(len(entries), 1)
        entry = entries[0]
        self.assertEqual(entry["heading"], "2026-07-30 - example")
        self.assertEqual(entry["base_seed_version"], "0.1.0")
        self.assertEqual(entry["disposition"], "repo-local")
        self.assertEqual(entry["paths_touched"], ["repo/knowledge/example.md"])
        self.assertEqual(entry["why"], ["Needed by this repository."])
        self.assertEqual(entry["evidence"], ["Checked by selftest."])

    def test_multiple_entries_do_not_bleed_into_each_other(self):
        text = (
            "## 2026-07-30 - first\n\nBase seed version: 0.1.0\nDisposition: repo-local\n"
            "Paths touched:\n- a.md\nWhy:\n- because\nEvidence:\n- checked\n"
            "## 2026-07-31 - second\n\nBase seed version: 0.2.0\nDisposition: promote-candidate\n"
            "Paths touched:\n- b.md\nWhy:\n- because\nEvidence:\n- checked\n"
        )
        entries = adaptations.parse_adaptation_ledger_text(text)
        self.assertEqual([entry["heading"] for entry in entries], ["2026-07-30 - first", "2026-07-31 - second"])
        self.assertEqual(entries[1]["paths_touched"], ["b.md"])


class ValidateAdaptationEntriesTests(unittest.TestCase):
    def test_well_formed_entry_passes(self):
        good = (
            "## 2026-07-30 - example\n\n"
            "Base seed version: 0.1.0\n"
            "Disposition: repo-local\n"
            "Paths touched:\n"
            "- repo/knowledge/example.md\n"
            "Why:\n"
            "- Needed by this repository.\n"
            "Evidence:\n"
            "- Checked by selftest.\n"
        )
        entries = adaptations.parse_adaptation_ledger_text(good)
        self.assertEqual(adaptations.validate_adaptation_entries(entries, "ledger"), [])

    def test_reports_missing_base_seed_version_and_bad_disposition(self):
        bad = "## 2026-07-30 - example\n\nDisposition: maybe\n"
        errors = adaptations.validate_adaptation_entries(adaptations.parse_adaptation_ledger_text(bad), "ledger")
        self.assertTrue(any("Base seed version" in error for error in errors))
        self.assertTrue(any("disposition" in error for error in errors))

    def test_reports_malformed_heading(self):
        bad = "## not-a-date - example\n\nBase seed version: 0.1.0\nDisposition: repo-local\n"
        errors = adaptations.validate_adaptation_entries(adaptations.parse_adaptation_ledger_text(bad), "ledger")
        self.assertTrue(any("YYYY-MM-DD - title" in error for error in errors))


class ValidateAdaptationsLedgerTests(unittest.TestCase):
    def test_absent_ledger_is_valid(self):
        ledger_path = _ledger_path()
        self.assertFalse(ledger_path.exists())
        self.assertEqual(adaptations.validate_adaptations_ledger(ledger_path, ledger_path.parent), [])

    def test_present_ledger_is_validated(self):
        ledger_path = _ledger_path()
        ledger_path.write_text("## 2026-07-30 - example\n\nDisposition: maybe\n", encoding="utf-8")
        errors = adaptations.validate_adaptations_ledger(ledger_path, ledger_path.parent)
        self.assertTrue(errors)


class LedgerEntriesForPathTests(unittest.TestCase):
    def test_finds_matching_heading(self):
        entries = [{"heading": "2026-07-30 - script-change", "paths_touched": [".hydra-framework/scripts/hydra.py"]}]
        self.assertEqual(adaptations.ledger_entries_for_path("scripts/hydra.py", entries), ["2026-07-30 - script-change"])

    def test_no_match_returns_empty(self):
        entries = [{"heading": "2026-07-30 - unrelated", "paths_touched": ["other.md"]}]
        self.assertEqual(adaptations.ledger_entries_for_path("scripts/hydra.py", entries), [])

    def test_entry_without_heading_is_ignored(self):
        entries = [{"heading": "", "paths_touched": ["scripts/hydra.py"]}]
        self.assertEqual(adaptations.ledger_entries_for_path("scripts/hydra.py", entries), [])


class FormatAdaptationEntryTests(unittest.TestCase):
    def test_formats_a_round_trippable_entry(self):
        text = adaptations.format_adaptation_entry(
            date_value="2026-07-30",
            title="example-change",
            base_seed_version="0.1.0",
            paths=[".hydra-framework/repo/knowledge/example.md"],
            why=["Needed by this repository."],
            evidence=["Checked by selftest."],
            disposition="repo-local",
        )
        entries = adaptations.parse_adaptation_ledger_text(text)
        self.assertEqual(len(entries), 1)
        self.assertEqual(entries[0]["heading"], "2026-07-30 - example-change")
        self.assertEqual(adaptations.validate_adaptation_entries(entries, "ledger"), [])
        self.assertIn("- repo/knowledge/example.md", text)


class AppendAdaptationEntryTests(unittest.TestCase):
    def test_creates_ledger_with_header_when_absent(self):
        ledger_path = _ledger_path()
        adaptations.append_adaptation_entry(ledger_path, "## 2026-07-30 - example\n")
        text = ledger_path.read_text(encoding="utf-8")
        self.assertTrue(text.startswith("# Adaptations Ledger\n"))
        self.assertIn("## 2026-07-30 - example", text)

    def test_never_rewrites_earlier_entries(self):
        ledger_path = _ledger_path()
        adaptations.append_adaptation_entry(ledger_path, "## 2026-07-30 - first\n")
        first = ledger_path.read_text(encoding="utf-8")
        adaptations.append_adaptation_entry(ledger_path, "## 2026-07-31 - second\n")
        second = ledger_path.read_text(encoding="utf-8")
        self.assertTrue(second.startswith(first.rstrip()))


class CurrentBaseSeedVersionTests(unittest.TestCase):
    def test_prefers_lineage_base_seed_version(self):
        manifest = {"seed_version": "0.2.0", "lineage": {"base_seed_version": "0.1.0"}}
        self.assertEqual(adaptations.current_base_seed_version(manifest), "0.1.0")

    def test_falls_back_to_seed_version_without_lineage(self):
        manifest = {"seed_version": "0.2.0"}
        self.assertEqual(adaptations.current_base_seed_version(manifest), "0.2.0")

    def test_falls_back_to_unknown_without_either(self):
        self.assertEqual(adaptations.current_base_seed_version({}), "unknown")


if __name__ == "__main__":
    unittest.main()
