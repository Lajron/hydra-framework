"""Location bundle for work commands.

`PERSONAL_TASKS_REL` duplicates `scripts/hydra.py`'s own module-level
constant of the same name rather than being imported from it: `hydra.py`
still needs its own copy for `resolver_paths()` and `envelope_schema_drift()`,
and the engine cannot import the shim.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

PERSONAL_TASKS_REL = "tasks/personal"
RETIRED_TASKS_REL = "tasks/retired"


@dataclass(frozen=True)
class WorkPaths:
    root: Path
    hydra: Path
    local: Path

    def personal_tasks_root(self) -> Path:
        return self.hydra / PERSONAL_TASKS_REL

    def owner_task_dir(self, owner: str) -> Path:
        return self.personal_tasks_root() / owner

    def local_notes_dir(self) -> Path:
        return self.local / "notes"

    def retired_tasks_root(self) -> Path:
        return self.local / RETIRED_TASKS_REL
