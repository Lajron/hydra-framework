"""Mirror test for `hydra_engine.checks.aggregation`."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

_SRC = Path(__file__).resolve().parents[3] / "src"
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

from hydra_engine.checks import aggregation  # noqa: E402
from hydra_engine.finding import Finding  # noqa: E402


class RunChecksTests(unittest.TestCase):
    def test_concatenates_every_checks_findings_in_order(self) -> None:
        first = Finding(path="a", code="one", detail="a is bad")
        second = Finding(path="b", code="two", detail="b is bad")
        result = aggregation.run_checks([lambda: [first], lambda: [second]])
        self.assertEqual(result, [first, second])

    def test_empty_checks_produce_nothing(self) -> None:
        self.assertEqual(aggregation.run_checks([]), [])

    def test_a_clean_check_contributes_nothing(self) -> None:
        finding = Finding(path="a", code="one", detail="a is bad")
        result = aggregation.run_checks([lambda: [], lambda: [finding]])
        self.assertEqual(result, [finding])


if __name__ == "__main__":
    unittest.main()
