"""Personal task state, tiers, and placement.

Owners, task records, notes, board rendering, tier boundaries, write-time
placement notices, and legacy state migration. `hydra.py`'s own top-level `slugify` is not
reused here; these modules import `identity.slugs.slugify` directly (see
`identity/slugs.py`'s docstring for why the two copies exist).
"""

from __future__ import annotations
