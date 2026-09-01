"""Cheap build-tool signals about the repository Hydra was copied into."""

from __future__ import annotations

from pathlib import Path

HOST_MARKERS = {
    "node": ["package.json", "pnpm-workspace.yaml", "turbo.json"],
    "python": ["pyproject.toml", "requirements.txt", "setup.py", "Pipfile"],
    "dotnet": ["*.sln", "*.csproj"],
    "go": ["go.mod"],
    "rust": ["Cargo.toml"],
    "java": ["pom.xml", "build.gradle", "build.gradle.kts"],
    "ruby": ["Gemfile"],
    "php": ["composer.json"],
}


def detect_host_repo(root: Path) -> dict[str, list[str]]:
    """Cheap signals about the repository Hydra was copied into."""
    found: dict[str, list[str]] = {}
    for stack, patterns in HOST_MARKERS.items():
        hits: list[str] = []
        for pattern in patterns:
            hits.extend(
                path.relative_to(root).as_posix()
                for path in sorted(root.glob(pattern))
                if path.is_file()
            )
        if hits:
            found[stack] = hits
    return found
