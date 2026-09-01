"""Mirror test for `hydra_engine.identity.slugs`."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

_SRC = Path(__file__).resolve().parents[3] / "src"
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

from hydra_engine.identity import slugs  # noqa: E402


class SlugifyTests(unittest.TestCase):
    def test_normalizes_separators_and_case(self):
        self.assertEqual(slugs.slugify("Token Efficiency Hooks"), "token-efficiency-hooks")
        self.assertEqual(slugs.slugify("  Mixed__Case/Slashes  "), "mixed-case-slashes")

    def test_empty_input_falls_back_to_task(self):
        self.assertEqual(slugs.slugify("!!!"), "task")
        self.assertEqual(slugs.slugify(""), "task")


if __name__ == "__main__":
    unittest.main()
