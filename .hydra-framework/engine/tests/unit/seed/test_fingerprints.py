"""Mirror test for `hydra_engine.seed.fingerprints`.

Split from `test_hydra.py`'s `SeedComparisonTests`, which hashed the live
repository tree directly (`hydra.HYDRA`); converted to a hermetic tmp tree
since the move itself is what makes that isolation possible, matching
clusters 5/7's precedent for unnamed live-repo-touching classes.
"""

from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

_SRC = Path(__file__).resolve().parents[3] / "src"
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

from hydra_engine.seed.fingerprints import hash_text, iter_framework_files  # noqa: E402


def _write(root: Path, rel: str, content: str = "") -> Path:
    path = root / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    return path


class HashTextTests(unittest.TestCase):
    def test_identical_text_hashes_identically(self):
        self.assertEqual(hash_text("hello"), hash_text("hello"))

    def test_different_text_hashes_differently(self):
        self.assertNotEqual(hash_text("hello"), hash_text("goodbye"))


class IterFrameworkFilesTests(unittest.TestCase):
    def test_skips_personal_records_but_keeps_templates(self):
        hydra_root = Path(tempfile.mkdtemp(prefix="seed-fingerprints-"))
        _write(hydra_root, "tasks/personal/dana/2026-01-01-example.md", "# Task\n")
        _write(hydra_root, "tasks/templates/task.md", "# Template\n")
        _write(hydra_root, "manifest.yaml", "seed_version: 0.1.0\n")

        files = iter_framework_files(hydra_root)

        self.assertFalse(
            [path for path in files if path.startswith("tasks/personal/")],
            "per-owner task records are work state, not framework definition",
        )
        self.assertIn("tasks/templates/task.md", files)
        self.assertIn("manifest.yaml", files)

    def test_skips_reflection_packets_but_keeps_the_reflections_readme(self):
        hydra_root = Path(tempfile.mkdtemp(prefix="seed-fingerprints-"))
        _write(hydra_root, "evolution/reflections/2026-08-01-example.md", "# Example\n")
        _write(hydra_root, "evolution/reflections/README.md", "# Reflection Queue\n")

        files = iter_framework_files(hydra_root)

        self.assertFalse(
            [path for path in files if path.startswith("evolution/reflections/") and path != "evolution/reflections/README.md"],
            "reflection packets are repo-local session artifacts, not framework definition",
        )
        self.assertIn("evolution/reflections/README.md", files)

    def test_excludes_cognition_and_transient_directories(self):
        hydra_root = Path(tempfile.mkdtemp(prefix="seed-fingerprints-"))
        _write(hydra_root, "cognition/graph/registry.yaml", "objects: []\n")
        _write(hydra_root, "capabilities/skills/__pycache__/example.pyc", "binary")
        _write(hydra_root, "capabilities/skills/.gitkeep")
        _write(hydra_root, "repo/knowledge/example.md", "# Example\n")

        files = iter_framework_files(hydra_root)

        self.assertNotIn("cognition/graph/registry.yaml", files)
        self.assertFalse([path for path in files if "__pycache__" in path])
        self.assertFalse([path for path in files if path.endswith(".gitkeep")])
        self.assertIn("repo/knowledge/example.md", files)

    def test_identical_trees_have_identical_hashes(self):
        hydra_root = Path(tempfile.mkdtemp(prefix="seed-fingerprints-"))
        _write(hydra_root, "manifest.yaml", "seed_version: 0.1.0\n")
        first = iter_framework_files(hydra_root)
        second = iter_framework_files(hydra_root)
        self.assertEqual(first, second)


if __name__ == "__main__":
    unittest.main()
