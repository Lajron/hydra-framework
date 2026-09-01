"""Knowledge-unit source freshness helpers."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Mapping

from hydra_engine.documents.digests import normalized_digest
from hydra_engine.documents.frontmatter_blocks import yaml_list
from hydra_engine.knowledge.packages import ContextCompilerPaths
from hydra_engine.ports import git as git_port

SOURCE_DIGEST_RE = re.compile(r"^sha256:[0-9a-f]{64}$")


def resolve_source_path(raw: str, paths: ContextCompilerPaths) -> Path:
    path = Path(raw)
    if path.is_absolute():
        return path
    return paths.root / raw


def valid_source_digest_entries(value: object) -> dict[str, str]:
    if not isinstance(value, (list, tuple)):
        return {}
    result: dict[str, str] = {}
    for entry in value:
        if not isinstance(entry, dict):
            continue
        source = entry.get("source")
        digest = entry.get("digest")
        if isinstance(source, str) and isinstance(digest, str):
            result[source] = digest
    return result


def stale_provenance_sources(
    provenance: Mapping[str, object],
    *,
    checked_on: str,
    paths: ContextCompilerPaths,
) -> list[str]:
    """Advisory stale source list for a unit provenance block.

    A source with a fingerprint compares file content. A source without one
    falls back to the existing date rule unchanged.
    """
    if not checked_on:
        return []
    stale: list[str] = []
    sources = yaml_list(provenance.get("sources"))
    digest_by_source = valid_source_digest_entries(provenance.get("source_digests"))
    for raw in sources:
        path = resolve_source_path(raw, paths)
        if raw in digest_by_source:
            if path.exists() and path.is_file() and normalized_digest(path) != digest_by_source[raw]:
                stale.append(raw)
            continue
        if not path.exists():
            continue
        commit_date = git_port.last_commit_iso(paths.root, raw)[:10]
        if commit_date and commit_date > checked_on:
            stale.append(raw)
    return stale
