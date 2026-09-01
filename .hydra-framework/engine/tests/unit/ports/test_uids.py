"""Mirror test for `hydra_engine.ports.uids`."""

from __future__ import annotations

import sys
import unittest
import uuid
from pathlib import Path

_SRC = Path(__file__).resolve().parents[3] / "src"
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

from hydra_engine.ports import uids  # noqa: E402


class UidsTests(unittest.TestCase):
    def test_new_uid_is_a_valid_uuid4_string(self):
        value = uids.new_uid()
        self.assertEqual(uuid.UUID(value).version, 4)

    def test_new_uid_is_not_constant(self):
        self.assertNotEqual(uids.new_uid(), uids.new_uid())


if __name__ == "__main__":
    unittest.main()
