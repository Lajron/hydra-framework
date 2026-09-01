"""Determinism and write-safety ports.

`clock`, `uids`, and `git` are the sole mediation points for "now", generated
identifiers, and git-derived state. Everything else in the engine reaches
these through here instead of calling `datetime`/`uuid`/`subprocess` directly,
so a golden fixture can freeze all three by patching one small surface. `fs`
is the sole mediation point for append-only and create-exclusive writes, the
two primitives that let a caller eliminate read-modify-write instead of
serializing it.
"""

from __future__ import annotations
