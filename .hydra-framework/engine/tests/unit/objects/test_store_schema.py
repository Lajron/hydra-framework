"""Mirror test for `hydra_engine.objects.store_schema`."""

from __future__ import annotations

import sqlite3
import sys
import unittest
from pathlib import Path

_SRC = Path(__file__).resolve().parents[3] / "src"
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

from hydra_engine.objects import store_schema  # noqa: E402

_EXPECTED_TABLES = {"documents", "refs", "objects", "aliases", "relations", "provenance", "tasks", "meta"}


class DefaultStorePathTests(unittest.TestCase):
    def test_lives_under_local_index(self):
        local = Path("/repo/.hydra-framework.local")
        self.assertEqual(store_schema.default_store_path(local), local / "index" / "object-store.db")


class CreateSchemaTests(unittest.TestCase):
    def test_creates_every_table(self):
        conn = sqlite3.connect(":memory:")
        store_schema.create_schema(conn)
        tables = {row[0] for row in conn.execute("SELECT name FROM sqlite_master WHERE type = 'table'")}
        self.assertEqual(tables, _EXPECTED_TABLES)
        conn.close()

    def test_records_the_schema_version_in_meta(self):
        conn = sqlite3.connect(":memory:")
        store_schema.create_schema(conn)
        self.assertTrue(store_schema.schema_matches(conn))
        self.assertEqual(store_schema.store_meta(conn)["schema"], store_schema.STORE_SCHEMA_VERSION)
        conn.close()


class SchemaMatchesTests(unittest.TestCase):
    def test_mismatched_schema_version_is_not_a_match(self):
        conn = sqlite3.connect(":memory:")
        conn.execute("CREATE TABLE meta (key TEXT PRIMARY KEY, value TEXT)")
        conn.execute("INSERT INTO meta VALUES ('schema', 'some-old-version')")
        self.assertFalse(store_schema.schema_matches(conn))
        conn.close()

    def test_missing_meta_table_is_not_a_match_rather_than_raising(self):
        conn = sqlite3.connect(":memory:")
        self.assertFalse(store_schema.schema_matches(conn))
        self.assertEqual(store_schema.store_meta(conn), {})
        conn.close()


if __name__ == "__main__":
    unittest.main()
