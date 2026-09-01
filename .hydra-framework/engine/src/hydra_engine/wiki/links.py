"""Markdown and Obsidian-style link validation.

`validate_markdown_links` checks a directory's plain `[text](target)` links;
`validate_obsidian_links` checks `[[wiki-link]]` links against a wiki root's
page names. Both take the repository root as an explicit argument (rule 1:
domain code takes `Path` arguments, never a module-global root) purely for
error-message display -- the same shape `display_path` already uses.
"""

from __future__ import annotations

import re
from pathlib import Path
from urllib.parse import unquote

from hydra_engine.documents.markdown import iter_markdown_files
from hydra_engine.documents.tokens import read_text
from hydra_engine.finding import Finding

MARKDOWN_LINK_RE = re.compile(r"\[[^\]]+\]\(([^)]+)\)")
OBSIDIAN_LINK_RE = re.compile(r"\[\[([^\]]+)\]\]")


def markdown_link_target(raw: str) -> str:
    target = raw.strip().strip("<>")
    if " " in target and not target.startswith("./"):
        target = target.split()[0]
    return unquote(target)


def validate_markdown_links(root: Path, repo_root: Path) -> list[Finding]:
    findings: list[Finding] = []
    for file in iter_markdown_files(root):
        base = file.parent
        for match in MARKDOWN_LINK_RE.finditer(read_text(file)):
            target = markdown_link_target(match.group(1))
            if not target or target.startswith("#"):
                continue
            if re.match(r"^[a-z][a-z0-9+.-]*:", target, re.IGNORECASE):
                continue
            path_part = target.split("#", 1)[0]
            if not path_part:
                continue
            candidate = (repo_root / path_part.lstrip("/")) if path_part.startswith("/") else (base / path_part)
            if not candidate.exists():
                label = str(file.relative_to(repo_root))
                findings.append(Finding(
                    path=label, code="markdown-links", detail=f"missing link: {label} -> {target}",
                ))
    return findings


def validate_root_relative_markdown_links(root: Path, repo_root: Path) -> list[Finding]:
    findings: list[Finding] = []
    for file in iter_markdown_files(root):
        label = str(file.relative_to(repo_root))
        for match in MARKDOWN_LINK_RE.finditer(read_text(file)):
            target = markdown_link_target(match.group(1))
            if target.startswith("../") or target.startswith("./../"):
                findings.append(Finding(
                    path=label,
                    code="markdown-link-paths",
                    detail=f"traversal link is not allowed: {label} -> {target}",
                ))
    return findings


def obsidian_link_target(raw: str) -> str:
    target = raw.split("|", 1)[0].split("#", 1)[0].strip()
    return unquote(target)


def obsidian_link_exists(target: str, base: Path, wiki_root: Path) -> bool:
    if not target or target.startswith("#"):
        return True
    if re.match(r"^[a-z][a-z0-9+.-]*:", target, re.IGNORECASE):
        return True

    raw = Path(target)
    candidates = [base / raw, wiki_root / raw]
    candidates.extend(candidate.with_suffix(".md") for candidate in list(candidates) if candidate.suffix == "")
    if any(candidate.exists() for candidate in candidates):
        return True

    if raw.suffix == "" and len(raw.parts) == 1:
        return any(wiki_root.rglob(f"{raw.name}.md"))
    return False


def validate_obsidian_links(wiki_root: Path, repo_root: Path) -> list[Finding]:
    if not wiki_root.exists():
        label = str(wiki_root.relative_to(repo_root))
        return [Finding(path=label, code="obsidian-links", detail=f"wiki root does not exist: {label}")]
    findings: list[Finding] = []
    for file in iter_markdown_files(wiki_root):
        base = file.parent
        for match in OBSIDIAN_LINK_RE.finditer(read_text(file)):
            target = obsidian_link_target(match.group(1))
            if not obsidian_link_exists(target, base, wiki_root):
                label = str(file.relative_to(repo_root))
                findings.append(Finding(
                    path=label, code="obsidian-links",
                    detail=f"missing wiki link: {label} -> [[{match.group(1)}]]",
                ))
    return findings


def validate_wiki(root: Path, repo_root: Path) -> list[Finding]:
    findings = validate_markdown_links(root, repo_root)
    findings.extend(validate_root_relative_markdown_links(root, repo_root))
    findings.extend(validate_obsidian_links(root, repo_root))
    return findings
