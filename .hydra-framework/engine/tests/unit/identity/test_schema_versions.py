"""Mirror test for `hydra_engine.identity.schema_versions`."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

_SRC = Path(__file__).resolve().parents[3] / "src"
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

from hydra_engine.identity import schema_versions  # noqa: E402


class SchemaVersionTests(unittest.TestCase):
    def test_ordering_of_the_version_ladder(self):
        self.assertLess(schema_versions.UNVERSIONED_SCHEMA_VERSION, schema_versions.UID_REQUIRED_FROM_SCHEMA_VERSION)
        self.assertLessEqual(
            schema_versions.UID_REQUIRED_FROM_SCHEMA_VERSION,
            schema_versions.ENVELOPE_REQUIRED_FROM_SCHEMA_VERSION,
        )
        self.assertLessEqual(schema_versions.ENVELOPE_REQUIRED_FROM_SCHEMA_VERSION, schema_versions.CURRENT_SCHEMA_VERSION)

    def test_envelope_schema_version_defaults_to_unversioned(self):
        self.assertEqual(schema_versions.envelope_schema_version({}), schema_versions.UNVERSIONED_SCHEMA_VERSION)
        self.assertEqual(schema_versions.envelope_schema_version({"schema_version": "2"}), 2)


if __name__ == "__main__":
    unittest.main()
