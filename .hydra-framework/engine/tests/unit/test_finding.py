"""Mirror tests for `hydra_engine.finding`."""

from __future__ import annotations

import unittest

from hydra_engine.finding import Finding


class FindingTests(unittest.TestCase):
    def test_str_reproduces_the_detail_text_verbatim(self) -> None:
        finding = Finding(path="a.md", code="example", detail="a.md is missing required title")
        self.assertEqual(str(finding), "a.md is missing required title")
        self.assertEqual(f"- {finding}", "- a.md is missing required title")

    def test_contains_proxies_to_detail(self) -> None:
        finding = Finding(path="a.md", code="example", detail="a.md is missing required title")
        self.assertIn("missing required title", finding)
        self.assertNotIn("nope", finding)

    def test_equality_is_structural(self) -> None:
        one = Finding(path="a.md", code="example", detail="x")
        two = Finding(path="a.md", code="example", detail="x")
        different = Finding(path="a.md", code="other", detail="x")
        self.assertEqual(one, two)
        self.assertNotEqual(one, different)


if __name__ == "__main__":
    unittest.main()
