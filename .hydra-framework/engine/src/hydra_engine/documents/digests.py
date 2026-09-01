"""Content digests for object envelopes."""

from __future__ import annotations

import hashlib
from pathlib import Path

from hydra_engine.documents.tokens import read_text


def normalized_digest(path: Path) -> str:
    text = read_text(path).replace("\r\n", "\n").replace("\r", "\n")
    return "sha256:" + hashlib.sha256(text.encode("utf-8")).hexdigest()
