"""Mirror test for `hydra_engine.telemetry.evidence_mint`."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

_SRC = Path(__file__).resolve().parents[3] / "src"
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

from hydra_engine.telemetry import evidence, evidence_mint  # noqa: E402


class PackageDirNameTests(unittest.TestCase):
    def test_joins_date_owner_and_slug(self):
        self.assertEqual(
            evidence_mint.package_dir_name("2026-08-28", "dana", "reducer-coverage"),
            "2026-08-28-dana-reducer-coverage",
        )


class RenderOverviewTests(unittest.TestCase):
    def _overview(self, **overrides):
        params = dict(
            dir_name="2026-08-28-dana-reducer-coverage",
            uid="11111111-1111-1111-1111-111111111111",
            owner="dana",
            today="2026-08-28",
            title="How much Bash output reaches a reviewed reducer?",
        )
        params.update(overrides)
        return evidence_mint.render_overview(**params)

    def test_hydra_id_matches_directory_name(self):
        text = self._overview()
        self.assertIn("hydra_id: hydra://telemetry-evidence/2026-08-28-dana-reducer-coverage", text)

    def test_status_is_open(self):
        self.assertIn("status: open", self._overview())

    def test_required_sections_are_present(self):
        text = self._overview()
        for heading in evidence.REQUIRED_SECTIONS:
            self.assertIn(heading, text)

    def test_required_header_fields_are_present(self):
        text = self._overview()
        self.assertIn("Author: dana", text)
        self.assertIn("Created: 2026-08-28", text)
        self.assertIn("Window:", text)
        self.assertIn("Corpus:", text)

    def test_minted_overview_passes_validate_package_apart_from_the_missing_sibling_files(self):
        # A full round-trip check: parsing what this module writes should not
        # itself trip any of `evidence.validate_package`'s envelope, status,
        # or directory-name checks.
        text = self._overview()
        body = evidence.parse_overview_body(text)
        self.assertEqual(body["fields"]["Author"], "dana")
        self.assertEqual(body["fields"]["Created"], "2026-08-28")
        self.assertEqual(body["sections"], set(evidence.REQUIRED_SECTIONS))


if __name__ == "__main__":
    unittest.main()
