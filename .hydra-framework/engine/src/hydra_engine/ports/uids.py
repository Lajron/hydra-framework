"""UID port.

The sole source of generated identifiers. Callers reach `new_uid()` as a
module function so a golden fixture can patch
`hydra_engine.ports.uids.new_uid` directly instead of patching `uuid` at
each call site.
"""

from __future__ import annotations

import uuid


def new_uid() -> str:
    return str(uuid.uuid4())
