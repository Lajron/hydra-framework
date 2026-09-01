"""Flat canonical knowledge-file validation.

Knowledge packages have their own package/unit validators. This module covers
only the legacy flat Markdown files directly under `repo/knowledge/`, excluding
the directory README, so they cannot remain unshaped canonical memory.
"""

from __future__ import annotations

import re
from pathlib import Path

from hydra_engine.documents.frontmatter_blocks import markdown_frontmatter, yaml_list, yaml_map, yaml_str
from hydra_engine.documents.tokens import HydraYamlError, cited_source_path_missing, display_path, read_text
from hydra_engine.finding import Finding

DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
PENDING_STATUSES = {"pending-discovery", "pending discovery"}
TERMINAL_CERTAINTIES = {"rejected", "superseded"}
SOURCE_SECTION_HEADINGS = {"## Sources", "## Source Material"}


def discover_flat_knowledge_files(hydra: Path) -> list[Path]:
    root = hydra / "repo" / "knowledge"
    if not root.is_dir():
        return []
    return sorted(path for path in root.glob("*.md") if path.name != "README.md")


def _source_key_present(data: dict) -> bool:
    return "sources" in yaml_map(data.get("provenance"))


def _sources(data: dict) -> list[str]:
    return yaml_list(yaml_map(data.get("provenance")).get("sources"))


def _date_value(data: dict) -> str:
    return yaml_str(data.get("updated")) or yaml_str(data.get("checked_on"))


def _certainty_head(value: str) -> str:
    return re.split(r"\s+-\s+|\s+", value.strip().lower(), maxsplit=1)[0]


def _h1(path: Path) -> str:
    for line in read_text(path).splitlines():
        if line.startswith("# "):
            return line.removeprefix("# ").strip()
    return ""


def _source_section_paths(path: Path) -> list[str]:
    paths: list[str] = []
    in_sources = False
    for line in read_text(path).splitlines():
        stripped = line.strip()
        if stripped.startswith("## "):
            in_sources = stripped in SOURCE_SECTION_HEADINGS
            continue
        if not in_sources or not stripped.startswith("- "):
            continue
        item = stripped.removeprefix("- ").strip()
        if item.startswith("`"):
            end = item.find("`", 1)
            if end > 1:
                paths.append(item[1:end])
            continue
        head = item.split(maxsplit=1)[0] if item else ""
        if "/" in head:
            paths.append(head.rstrip(".,;:"))
    return paths


def validate_flat_knowledge_files(hydra: Path, root: Path) -> list[Finding]:
    findings: list[Finding] = []
    titles: dict[str, list[str]] = {}

    for path in discover_flat_knowledge_files(hydra):
        rel = display_path(path, root)
        try:
            data = markdown_frontmatter(path, root)
        except HydraYamlError as error:
            findings.append(Finding(path=rel, code="flat-knowledge", detail=str(error)))
            continue

        if not data:
            findings.append(Finding(
                path=rel, code="flat-knowledge",
                detail=f"{rel}: missing flat knowledge frontmatter envelope",
            ))
            continue

        title = yaml_str(data.get("title"))
        status = yaml_str(data.get("status"))
        owners = yaml_map(data.get("owners"))
        certainty = yaml_str(data.get("certainty"))
        date = _date_value(data)

        for field, value in (("title", title), ("status", status)):
            if not value:
                findings.append(Finding(path=rel, code="flat-knowledge", detail=f"{rel}: missing `{field}`"))
        if not owners:
            findings.append(Finding(path=rel, code="flat-knowledge", detail=f"{rel}: missing `owners`"))
        if not certainty and not date:
            findings.append(Finding(
                path=rel, code="flat-knowledge",
                detail=f"{rel}: missing `certainty` or `updated`/`checked_on` date",
            ))
        if date and not DATE_RE.match(date):
            findings.append(Finding(
                path=rel, code="flat-knowledge",
                detail=f"{rel}: `updated`/`checked_on` date must be YYYY-MM-DD",
            ))

        normalized_status = status.strip().lower()
        if normalized_status not in PENDING_STATUSES and not _source_key_present(data):
            findings.append(Finding(
                path=rel, code="flat-knowledge",
                detail=f"{rel}: active flat knowledge requires `provenance.sources`",
            ))
        for raw in _sources(data):
            if cited_source_path_missing(raw, path.parent, root):
                findings.append(Finding(
                    path=rel, code="flat-knowledge",
                    detail=f"{rel}: `provenance.sources` path does not exist: {raw}",
                ))
        for raw in _source_section_paths(path):
            if cited_source_path_missing(raw, path.parent, root):
                findings.append(Finding(
                    path=rel, code="flat-knowledge",
                    detail=f"{rel}: source list path does not exist: {raw}",
                ))

        certainty_head = _certainty_head(certainty)
        if normalized_status == "active" and certainty_head in TERMINAL_CERTAINTIES:
            findings.append(Finding(
                path=rel, code="flat-knowledge",
                detail=f"{rel}: status `active` contradicts certainty `{certainty_head}`",
            ))
        if normalized_status in PENDING_STATUSES and certainty_head == "confirmed":
            findings.append(Finding(
                path=rel, code="flat-knowledge",
                detail=f"{rel}: pending status contradicts certainty `confirmed`",
            ))

        visible_title = title or _h1(path)
        if visible_title:
            titles.setdefault(visible_title.strip().lower(), []).append(rel)

    for matches in titles.values():
        if len(matches) > 1:
            joined = ", ".join(matches)
            findings.append(Finding(
                path="",
                code="flat-knowledge",
                detail=f"duplicate flat knowledge title across {joined}",
            ))

    return findings
