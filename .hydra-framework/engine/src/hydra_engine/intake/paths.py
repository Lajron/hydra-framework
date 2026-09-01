"""Location bundle for intake commands."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class IntakePaths:
    root: Path
    hydra: Path

    def staging_root(self) -> Path:
        return self.root / ".migrations"

    def workspace_root(self) -> Path:
        return self.hydra / "intake/migrations"

    def integration_workspace_root(self) -> Path:
        return self.hydra / "intake/integrations"
