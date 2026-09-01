"""takeover goldens."""

from __future__ import annotations

import unittest

from .fixtures import assert_golden, run_golden


class TakeoverGoldenTests(unittest.TestCase):
    def test_takeover_scan_happy_path(self):
        outcome = run_golden(
            ["takeover", "scan"],
            extra_fixture={".cursorrules": "Use Cursor rules.\n"},
        )
        assert_golden(self, "takeover-scan", outcome)

    def test_takeover_scan_json(self):
        outcome = run_golden(
            ["takeover", "scan", "--json"],
            extra_fixture={".cursorrules": "Use Cursor rules.\n"},
        )
        assert_golden(self, "takeover-scan-json", outcome)


if __name__ == "__main__":
    unittest.main()
