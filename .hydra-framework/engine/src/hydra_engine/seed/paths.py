"""Location bundle for seed-comparison commands.

`adaptation_ledger` is a field, not a method computed from `hydra` the way
`InstallationPaths.manifest_path()` is: `hydra.py`'s own `ADAPTATION_LEDGER`
global is independently swappable (by `RepoContext` and by tests), not always
`hydra / "evolution/adaptations.md"`, so this dataclass takes the resolved
path directly, matching `ObjectLocations.object_registry`'s same shape for
the same reason.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class SeedPaths:
    root: Path
    hydra: Path
    adaptation_ledger: Path
