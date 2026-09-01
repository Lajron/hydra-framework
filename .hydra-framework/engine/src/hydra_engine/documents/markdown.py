"""Markdown file discovery and prose scanning."""

from __future__ import annotations

from pathlib import Path

from hydra_engine.documents.tokens import read_text


def iter_markdown_files(root: Path) -> list[Path]:
    skipped = {".git", "node_modules", "dist", "build", ".hydra-framework.local"}
    files: list[Path] = []
    for item in sorted(root.rglob("*.md")):
        if any(part in skipped for part in item.parts):
            continue
        files.append(item)
    return files


def strip_markdown_code_fences(text: str) -> str:
    """Remove fenced examples before scanning prose for object references."""
    lines: list[str] = []
    in_fence = False
    for line in text.splitlines():
        if line.lstrip().startswith("```"):
            in_fence = not in_fence
            lines.append("")
        elif in_fence:
            lines.append("")
        else:
            lines.append(line)
    return "\n".join(lines)


def first_markdown_heading(path: Path) -> str:
    for line in read_text(path).splitlines():
        if line.startswith("# "):
            return line[2:].strip()
    return ""
