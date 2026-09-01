"""Mirror test for `hydra_engine.knowledge.freshness`."""

from __future__ import annotations

import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

_SRC = Path(__file__).resolve().parents[3] / "src"
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

from hydra_engine.documents.digests import normalized_digest  # noqa: E402
from hydra_engine.knowledge import freshness  # noqa: E402
from hydra_engine.knowledge.packages import ContextCompilerPaths  # noqa: E402


class FreshnessTests(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.root = Path(self._tmp.name)
        subprocess.run(["git", "init", "-q"], cwd=str(self.root), check=True)
        subprocess.run(["git", "config", "user.email", "fixture@example.com"], cwd=str(self.root), check=True)
        subprocess.run(["git", "config", "user.name", "Fixture"], cwd=str(self.root), check=True)
        (self.root / "source.py").write_text("x = 1\n", encoding="utf-8")
        subprocess.run(["git", "add", "source.py"], cwd=str(self.root), check=True)
        subprocess.run(["git", "commit", "-q", "-m", "fixture commit"], cwd=str(self.root), check=True)
        self.paths = ContextCompilerPaths(root=self.root, hydra=self.root / ".hydra-framework")

    def test_source_with_matching_digest_is_not_stale_by_date(self):
        digest = normalized_digest(self.root / "source.py")
        stale = freshness.stale_provenance_sources(
            {
                "sources": ["source.py"],
                "source_digests": [{"source": "source.py", "digest": digest}],
            },
            checked_on="2000-01-01",
            paths=self.paths,
        )
        self.assertEqual(stale, [])

    def test_source_without_digest_uses_date_fallback(self):
        stale = freshness.stale_provenance_sources(
            {"sources": ["source.py"]},
            checked_on="2000-01-01",
            paths=self.paths,
        )
        self.assertEqual(stale, ["source.py"])

    def test_changed_fingerprinted_source_is_stale(self):
        digest = normalized_digest(self.root / "source.py")
        (self.root / "source.py").write_text("x = 2\n", encoding="utf-8")
        stale = freshness.stale_provenance_sources(
            {
                "sources": ["source.py"],
                "source_digests": [{"source": "source.py", "digest": digest}],
            },
            checked_on="2099-01-01",
            paths=self.paths,
        )
        self.assertEqual(stale, ["source.py"])


if __name__ == "__main__":
    unittest.main()
