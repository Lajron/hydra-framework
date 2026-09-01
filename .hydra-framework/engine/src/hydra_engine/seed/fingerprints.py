"""Content-hash fingerprints of a framework tree."""

from __future__ import annotations

import hashlib
from pathlib import Path

from hydra_engine.documents.tokens import read_text


def hash_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def iter_framework_files(hydra_root: Path) -> dict[str, str]:
    """Content hashes for every shared framework file under a Hydra root.

    Compares framework *definition*, not repository content. Task records are
    per-person work state, so they are excluded; task *templates* are definition
    and are compared, which is how template drift between a seed and a copy
    becomes visible at all. Reflection *packets* under `evolution/reflections/`
    are repo-local session artifacts for the same reason task records are
    excluded, but `evolution/reflections/README.md` is the packet contract
    itself, so it is kept comparable -- mirroring why `tasks/templates/` stays
    compared while `tasks/personal/` does not.
    """
    excluded_tops = {"cognition"}
    excluded_prefixes = ("tasks/personal", "evolution/reflections")
    included_despite_prefix = {"evolution/reflections/README.md"}
    excluded_parts = {".git", "__pycache__", "images"}
    files: dict[str, str] = {}
    for path in sorted(hydra_root.rglob("*")):
        if not path.is_file():
            continue
        rel = path.relative_to(hydra_root)
        rel_str = rel.as_posix()
        if rel.parts and rel.parts[0] in excluded_tops:
            continue
        if rel_str not in included_despite_prefix and rel_str.startswith(excluded_prefixes):
            continue
        if any(part in excluded_parts for part in rel.parts):
            continue
        if path.name == ".gitkeep":
            continue
        files[rel_str] = hash_text(read_text(path))
    return files
