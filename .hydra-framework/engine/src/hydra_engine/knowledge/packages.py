"""Knowledge package location and discovery."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class ContextCompilerPaths:
    root: Path
    hydra: Path

    def knowledge_packages_root(self) -> Path:
        return self.hydra / "repo/knowledge/knowledge-packages"

    def hydra_script(self) -> Path:
        return self.hydra / "scripts/hydra.py"


def discover_knowledge_packages(paths: ContextCompilerPaths) -> list[Path]:
    packages = paths.knowledge_packages_root()
    if not packages.exists():
        return []
    roots: list[Path] = []
    for item in sorted(packages.iterdir()):
        if not item.is_dir() or item.name == "templates":
            continue
        if any((item / marker).exists() for marker in ["overview.md", "routing.yaml", "units", "architecture"]):
            roots.append(item)
    return roots


def knowledge_package_root_for_path(path: Path, paths: ContextCompilerPaths) -> Path | None:
    packages = paths.knowledge_packages_root()
    try:
        rel = path.resolve().relative_to(packages.resolve())
    except ValueError:
        return None
    if not rel.parts or rel.parts[0] == "templates":
        return None
    return packages / rel.parts[0]
