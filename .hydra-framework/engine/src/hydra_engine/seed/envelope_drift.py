"""Detect envelope schema-version drift against a base seed.

The base `ObjectLocations` reuses `local_paths.personal_tasks_rel` rather
than taking a separate parameter: it is the same repository-shape constant
either side of a diff-base comparison, and `local_paths` already carries it.
"""

from __future__ import annotations

from pathlib import Path

from hydra_engine.objects.discovery import ObjectLocations, collect_hydra_objects
from hydra_engine.seed.adaptations import normalize_adaptation_path


def envelope_schema_drift(local_paths: ObjectLocations, base_hydra: Path) -> dict[str, str]:
    """Paths whose only known-explainable difference from base is being
    behind on `schema_version` (the first resolved architecture gap).

    Returns nothing (rather than raising) when either side fails to parse -
    `diff-base` still reports the raw content difference as unexplained in
    that case, which is no worse than before this existed.
    """
    local_objects, local_errors = collect_hydra_objects(local_paths)
    if local_errors:
        return {}
    base_paths = ObjectLocations(
        root=base_hydra.parent,
        hydra=base_hydra,
        local=base_hydra.parent / ".hydra-framework.local",
        personal_tasks_rel=local_paths.personal_tasks_rel,
        object_registry=base_hydra / "cognition/graph/registry.yaml",
    )
    base_objects, base_errors = collect_hydra_objects(base_paths)
    if base_errors:
        return {}

    local_versions = {normalize_adaptation_path(obj["path"]): obj["schema_version"] for obj in local_objects}
    base_versions = {normalize_adaptation_path(obj["path"]): obj["schema_version"] for obj in base_objects}

    drift: dict[str, str] = {}
    for path, base_version in base_versions.items():
        local_version = local_versions.get(path)
        if local_version is not None and local_version < base_version:
            drift[path] = (
                f"schema_version {local_version} behind base ({base_version}); "
                "run `hydra.py schema upgrade`"
            )
    return drift
