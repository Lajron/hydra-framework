"""`hydra://` id/ref shapes and object families."""

from __future__ import annotations

import re
from pathlib import Path

from hydra_engine.documents.markdown import strip_markdown_code_fences

HYDRA_ID_RE = re.compile(r"^hydra://[a-z0-9][a-z0-9-]*(?:/[a-z0-9][a-z0-9-]*)+$")
HYDRA_REF_RE = re.compile(r"hydra://[A-Za-z0-9][A-Za-z0-9-]*(?:/[A-Za-z0-9][A-Za-z0-9-]*)+")

def hydra_refs_in_text(path: Path, text: str) -> list[str]:
    body = strip_markdown_code_fences(text) if path.suffix == ".md" else text
    return sorted({match.group(0).lower() for match in HYDRA_REF_RE.finditer(body)})


def hydra_refs_by_line(path: Path, text: str) -> list[tuple[int, str]]:
    """Every `hydra://` reference with its 1-based line number, for the
    operational query store's `refs` table. Unlike
    `hydra_refs_in_text`, this keeps each occurrence and its site rather than
    deduplicating per file: the store answers "what cites `X`, and where,"
    which needs every site, not just whether one exists."""
    body = strip_markdown_code_fences(text) if path.suffix == ".md" else text
    refs: list[tuple[int, str]] = []
    for line_number, line in enumerate(body.splitlines(), start=1):
        refs.extend((line_number, match.group(0).lower()) for match in HYDRA_REF_RE.finditer(line))
    return refs


def hydra_id_prefix(hydra_id: str) -> str:
    """The first path segment of an `hydra://` id; `""` for anything else.

    Id shape stays here with the two regexes. Which families claim which
    prefix moved to `identity.object_families` (the first
    extension registry), along with the `OBJECT_FAMILIES` map and
    `hydra_object_family` that used to live in this module.
    """
    scheme, _, rest = hydra_id.partition("://")
    return rest.split("/", 1)[0] if scheme == "hydra" else ""
