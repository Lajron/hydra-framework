"""Command layer.

Each `commands/<x>.py` module holds one command family's decision logic and
returns `CommandResult` rather than a bare exit code. Printing mostly happens
here, outside the few commands with a dedicated `cli/` rendering layer; this
layer and `cli/` are the two allowed to produce strings.
"""

from __future__ import annotations

import dataclasses


@dataclasses.dataclass(frozen=True)
class CommandResult:
    exit_code: int
