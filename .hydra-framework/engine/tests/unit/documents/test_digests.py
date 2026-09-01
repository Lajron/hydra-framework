"""Mirror test for `hydra_engine.documents.digests`."""

from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

_SRC = Path(__file__).resolve().parents[3] / "src"
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

from hydra_engine.documents import digests  # noqa: E402


class DigestTests(unittest.TestCase):
    def test_digest_is_stable_and_prefixed(self):
        root = Path(tempfile.mkdtemp(prefix="digests-test-"))
        path = root / "obj.md"
        path.write_text("content\n", encoding="utf-8")
        digest = digests.normalized_digest(path)
        self.assertTrue(digest.startswith("sha256:"))
        self.assertEqual(digest, digests.normalized_digest(path))

    def test_digest_normalizes_line_endings(self):
        root = Path(tempfile.mkdtemp(prefix="digests-test-"))
        unix_path = root / "unix.md"
        crlf_path = root / "crlf.md"
        unix_path.write_bytes(b"a\nb\n")
        crlf_path.write_bytes(b"a\r\nb\r\n")
        self.assertEqual(digests.normalized_digest(unix_path), digests.normalized_digest(crlf_path))


if __name__ == "__main__":
    unittest.main()
