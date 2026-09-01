"""Mirror test for `hydra_engine.knowledge.surfaces`."""

from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

_SRC = Path(__file__).resolve().parents[3] / "src"
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

from hydra_engine.knowledge import surfaces  # noqa: E402
from hydra_engine.knowledge.packages import ContextCompilerPaths  # noqa: E402


def _paths_with_entry_files() -> ContextCompilerPaths:
    root = Path(tempfile.mkdtemp(prefix="surfaces-test-"))
    (root / "AI_SYSTEM.md").write_text("# Entry\n\nSome content.\n", encoding="utf-8")
    (root / "AGENTS.md").write_text("# Agents\n", encoding="utf-8")
    return ContextCompilerPaths(root=root, hydra=root / ".hydra-framework")


class IterSurfaceFilesTests(unittest.TestCase):
    def test_finds_entry_files_by_default(self):
        paths = _paths_with_entry_files()
        files = surfaces.iter_surface_files(paths)
        self.assertEqual({p.name for _, p in files}, {"AI_SYSTEM.md", "AGENTS.md"})

    def test_extra_path_file_is_included_once(self):
        paths = _paths_with_entry_files()
        extra = paths.root / "AI_SYSTEM.md"
        files = surfaces.iter_surface_files(paths, extra_paths=[str(extra)])
        matches = [p for _, p in files if p == extra]
        self.assertEqual(len(matches), 1)

    def test_extra_path_directory_globs_markdown_files(self):
        paths = _paths_with_entry_files()
        extra_dir = paths.root / "notes"
        extra_dir.mkdir()
        (extra_dir / "note.md").write_text("note\n", encoding="utf-8")
        files = surfaces.iter_surface_files(paths, extra_paths=[str(extra_dir)])
        self.assertIn(("custom", extra_dir / "note.md"), files)


class MeasureContextSurfacesTests(unittest.TestCase):
    def test_reports_totals_consistent_with_rows(self):
        paths = _paths_with_entry_files()
        rows, totals = surfaces.measure_context_surfaces(paths)
        self.assertTrue(rows)
        self.assertGreater(totals["approx_tokens"], 0)
        self.assertEqual(totals["approx_tokens"], sum(int(row["approx_tokens"]) for row in rows))
        self.assertEqual(totals["chars"], sum(int(row["chars"]) for row in rows))


if __name__ == "__main__":
    unittest.main()
