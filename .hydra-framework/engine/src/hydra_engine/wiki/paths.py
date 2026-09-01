"""Location bundle for wiki commands."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class WikiPaths:
    root: Path
    project_wiki: Path
