"""Mirror test for `hydra_engine.installation.host_detection`."""

from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

_SRC = Path(__file__).resolve().parents[3] / "src"
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

from hydra_engine.installation.host_detection import detect_host_repo  # noqa: E402


class DetectHostRepoTests(unittest.TestCase):
    def _root(self) -> Path:
        return Path(tempfile.mkdtemp(prefix="host-detection-"))

    def test_no_markers_found(self):
        root = self._root()
        self.assertEqual(detect_host_repo(root), {})

    def test_detects_python_and_node_markers(self):
        root = self._root()
        (root / "pyproject.toml").write_text("[project]\n", encoding="utf-8")
        (root / "package.json").write_text("{}\n", encoding="utf-8")
        found = detect_host_repo(root)
        self.assertEqual(found["python"], ["pyproject.toml"])
        self.assertEqual(found["node"], ["package.json"])
        self.assertNotIn("go", found)

    def test_glob_markers_resolve_relative_to_root(self):
        root = self._root()
        (root / "example.csproj").write_text("<Project />\n", encoding="utf-8")
        found = detect_host_repo(root)
        self.assertEqual(found["dotnet"], ["example.csproj"])


if __name__ == "__main__":
    unittest.main()
