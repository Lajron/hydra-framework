"""Provider adapter logic.

Capability-class/effort-budget resolution, provider skill/agent wrapper
generation, the single `planned_adapter_files()` plan those wrappers and
`export-adapters`/`reclaim` both read, and reclaim/notice logic for
hand-authored files in provider-native directories. `provider_surface_notice`
lives in `reclaim.py` rather than a separate `notices.py`: it is a thin
wrapper around `classify_surfaces()` with no other cross-cutting need, and a
near-empty module would exist only to match a plan table's parenthetical
wording -- the same reasoning that folded `notes.py` into `commands/work.py`.
"""

from __future__ import annotations
