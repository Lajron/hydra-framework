"""Slug normalization.

Moved from `engine/context_compiler.py`, which is the only one of the
source files that actually defined a slugify; `hydra.py` keeps its own
separate copy, as it does for the rest of the restricted-YAML/Markdown
vocabulary this slice does not touch.
"""

from __future__ import annotations

import re


def slugify(value: str) -> str:
    value = value.strip().lower()
    value = re.sub(r"[^a-z0-9]+", "-", value)
    return value.strip("-") or "task"
