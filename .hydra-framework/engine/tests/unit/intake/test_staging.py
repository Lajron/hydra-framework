"""Mirror test for `hydra_engine.intake.staging`."""

from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

_SRC = Path(__file__).resolve().parents[3] / "src"
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

from hydra_engine.intake import staging  # noqa: E402
from hydra_engine.intake.paths import IntakePaths  # noqa: E402


def _paths() -> IntakePaths:
    root = Path(tempfile.mkdtemp(prefix="intake-staging-"))
    return IntakePaths(root=root, hydra=root / ".hydra-framework")


class MigrationSourceNameTests(unittest.TestCase):
    def test_strips_leading_dot_and_slugifies(self):
        self.assertEqual(staging.migration_source_name(Path("/tmp/.legacy_ai")), "legacy-ai")

    def test_plain_name_slugifies(self):
        self.assertEqual(staging.migration_source_name(Path("/tmp/Legacy AI")), "legacy-ai")


class ValidateMigrationSlugTests(unittest.TestCase):
    def test_accepts_already_normalized_slug(self):
        self.assertEqual(staging.validate_migration_slug("legacy-ai"), "legacy-ai")

    def test_rejects_slug_with_slash(self):
        with self.assertRaises(ValueError):
            staging.validate_migration_slug("legacy/ai")

    def test_rejects_slug_that_would_normalize_differently(self):
        with self.assertRaises(ValueError):
            staging.validate_migration_slug("Legacy AI")

    def test_rejects_empty_slug(self):
        with self.assertRaises(ValueError):
            staging.validate_migration_slug("")


class IterMigrationSourceRootsTests(unittest.TestCase):
    def test_missing_staging_root_returns_empty(self):
        paths = _paths()
        self.assertEqual(staging.iter_migration_source_roots(paths), [])

    def test_lists_sources_ignoring_readme_and_gitkeep(self):
        paths = _paths()
        root = paths.staging_root()
        (root / "legacy-ai").mkdir(parents=True)
        (root / "other").mkdir(parents=True)
        (root / "README.md").write_text("x\n", encoding="utf-8")
        (root / ".gitkeep").write_text("", encoding="utf-8")
        names = sorted(path.name for path in staging.iter_migration_source_roots(paths))
        self.assertEqual(names, ["legacy-ai", "other"])

    def test_scoped_to_slug_returns_single_match_when_present(self):
        paths = _paths()
        root = paths.staging_root()
        (root / "legacy-ai").mkdir(parents=True)
        (root / "other").mkdir(parents=True)
        found = staging.iter_migration_source_roots(paths, "legacy-ai")
        self.assertEqual([path.name for path in found], ["legacy-ai"])

    def test_scoped_to_missing_slug_returns_empty(self):
        paths = _paths()
        self.assertEqual(staging.iter_migration_source_roots(paths, "nope"), [])


if __name__ == "__main__":
    unittest.main()
