"""Context-surface measurement: which files load into every prompt, and how
big they are.

`approx_tokens` is not redefined here -- it's `knowledge/candidates.py`'s copy
(byte-identical to the one this module's logic used before the move; verified
before reuse), reused rather than duplicated a third time.
"""

from __future__ import annotations

from pathlib import Path

from hydra_engine.documents.tokens import display_path, read_text
from hydra_engine.knowledge.candidates import APPROX_CHARS_PER_TOKEN, approx_tokens
from hydra_engine.knowledge.packages import ContextCompilerPaths

DEFAULT_CONTEXT_SURFACES = [
    ("entry", "AI_SYSTEM.md"),
    ("entry", "AGENTS.md"),
    ("entry", "CLAUDE.md"),
    ("adapter-doc", ".hydra-framework/adapters/providers/*/README.md"),
    ("capability", ".hydra-framework/capabilities/tools/capabilities.yaml"),
    ("claude-rule", ".claude/rules/**/*.md"),
    ("codex-doc", ".codex/**/*.md"),
]
GENERATED_SKILL_SURFACES = [
    ("generated-skill", ".claude/skills/*/SKILL.md"),
    ("generated-skill", ".agents/skills/*/SKILL.md"),
]


def iter_surface_files(
    paths: ContextCompilerPaths,
    include_generated_skills: bool = False,
    extra_paths: list[str] | None = None,
) -> list[tuple[str, Path]]:
    patterns = list(DEFAULT_CONTEXT_SURFACES)
    if include_generated_skills:
        patterns.extend(GENERATED_SKILL_SURFACES)

    seen: set[Path] = set()
    files: list[tuple[str, Path]] = []
    for category, pattern in patterns:
        for path in sorted(paths.root.glob(pattern)):
            if path.is_file() and path not in seen:
                seen.add(path)
                files.append((category, path))

    for raw in extra_paths or []:
        path = Path(raw)
        if not path.is_absolute():
            path = paths.root / path
        if path.is_file() and path not in seen:
            seen.add(path)
            files.append(("custom", path))
        elif path.is_dir():
            for item in sorted(path.rglob("*.md")):
                if item.is_file() and item not in seen:
                    seen.add(item)
                    files.append(("custom", item))
    return files


def measure_context_surfaces(
    paths: ContextCompilerPaths,
    include_generated_skills: bool = False,
    extra_paths: list[str] | None = None,
    chars_per_token: int = APPROX_CHARS_PER_TOKEN,
) -> tuple[list[dict[str, int | str]], dict[str, int]]:
    rows: list[dict[str, int | str]] = []
    totals = {"chars": 0, "lines": 0, "approx_tokens": 0}
    for category, path in iter_surface_files(paths, include_generated_skills, extra_paths):
        text = read_text(path)
        chars = len(text)
        lines = len(text.splitlines())
        tokens = approx_tokens(text, chars_per_token)
        totals["chars"] += chars
        totals["lines"] += lines
        totals["approx_tokens"] += tokens
        rows.append({
            "category": category,
            "path": display_path(path, paths.root),
            "chars": chars,
            "lines": lines,
            "approx_tokens": tokens,
        })
    return rows, totals
