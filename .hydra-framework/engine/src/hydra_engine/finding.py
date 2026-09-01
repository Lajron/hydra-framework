"""Structured validator output.

Loose at the package root, like `architecture.py`: every layer from
`objects/` (1) up through `commands/` (4) needs to construct or consume a
`Finding`, so it cannot live inside any single layer without an upward
import somewhere. `_layer_of` (see `architecture.py`) assigns `layer=None`
to any module directly under the package root, which check 3 (layer
direction) never treats as an upward-import target — the same exemption
`architecture.py` itself already relies on. Zero internal imports keeps it
inside check 4's exemption for high in-degree regardless of how many
modules end up importing it.

`detail` is the exact message text a `validate_*` function used to return
bare in its `list[str]`, byte-for-byte unchanged -- the conversion adds
structure around existing text rather than reformatting it, which is what
keeps every prior golden byte-identical. `path` is a best-effort single
path/entity the finding is about (empty string when a message spans more
than one, e.g. a duplicate id across several files) for callers that want
to query structurally instead of parsing prose. `code` is a stable
kebab-case identifier of which check produced the finding, one per
producing function rather than per message shape inside it -- fine-grained
sub-codes are not asked for by anything today.

`__str__` reproduces today's exact message text, so `print(f"- {finding}")`
is byte-identical to the old `print(f"- {error}")` over a `list[str]`.
`__contains__` proxies to `detail` so pre-existing `assertIn(sub, finding)`
/ `any(sub in f for f in findings)` call sites keep working unmodified --
`Finding` is deliberately not a `str` subclass (that would blur the
structural fields into string identity), so this is the one bit of
string-like behavior added back, scoped to substring containment only.
"""

from __future__ import annotations

import dataclasses


@dataclasses.dataclass(frozen=True)
class Finding:
    path: str
    code: str
    detail: str

    def __str__(self) -> str:
        return self.detail

    def __contains__(self, substring: str) -> bool:
        return substring in self.detail
