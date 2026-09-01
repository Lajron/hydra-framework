"""Location bundle for installation commands."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class InstallationPaths:
    root: Path
    hydra: Path

    def manifest_path(self) -> Path:
        return self.hydra / "manifest.yaml"

    def hooks_dir(self) -> Path:
        return self.hydra / "hooks"
