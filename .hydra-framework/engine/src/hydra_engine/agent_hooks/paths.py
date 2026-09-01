"""Location bundle for agent-hook commands."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class AgentHooksPaths:
    root: Path
    local: Path
