"""Mirror test for `hydra_engine.identity.hydra_ids`."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

_SRC = Path(__file__).resolve().parents[3] / "src"
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

from hydra_engine.identity import hydra_ids  # noqa: E402


class HydraIdShapeTests(unittest.TestCase):
    def test_hydra_id_re_matches_well_formed_ids(self):
        self.assertTrue(hydra_ids.HYDRA_ID_RE.match("hydra://knowledge-unit/0001-test"))
        self.assertFalse(hydra_ids.HYDRA_ID_RE.match("hydra://Knowledge-Unit/0001-test"))
        self.assertFalse(hydra_ids.HYDRA_ID_RE.match("not-a-hydra-id"))

    def test_hydra_refs_in_text_skips_code_fences(self):
        text = "See hydra://knowledge-unit/0001-test.\n```\nhydra://knowledge-unit/9999-fenced\n```\n"
        refs = hydra_ids.hydra_refs_in_text(Path("doc.md"), text)
        self.assertEqual(refs, ["hydra://knowledge-unit/0001-test"])

    def test_hydra_id_prefix_reads_the_first_segment_only(self):
        # Which family claims that prefix is `identity.object_families`'
        # question now; this module only knows id shape.
        self.assertEqual(hydra_ids.hydra_id_prefix("hydra://knowledge-slice/pkg/state"), "knowledge-slice")
        self.assertEqual(hydra_ids.hydra_id_prefix("hydra://knowledge-unit/0001-test"), "knowledge-unit")
        self.assertEqual(hydra_ids.hydra_id_prefix("not-a-hydra-id"), "")
        self.assertEqual(hydra_ids.hydra_id_prefix(""), "")


if __name__ == "__main__":
    unittest.main()
