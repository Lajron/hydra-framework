"""Location bundle for provider commands."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class ProvidersPaths:
    root: Path
    hydra: Path

    def capability_map_path(self, provider: str) -> Path:
        return self.hydra / "adapters/providers" / provider / "capability-map.yaml"

    def skills_root(self) -> Path:
        return self.hydra / "capabilities/skills"

    def agents_root(self) -> Path:
        return self.hydra / "capabilities/agents"

    def canonical_module_dir(self, kind: str) -> Path:
        return self.hydra / ("capabilities/agents" if kind == "agent" else "capabilities/skills")
