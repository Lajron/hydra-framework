"""Inventory and approved side effects for migration approval batches."""

from __future__ import annotations

import shutil
from pathlib import Path

from hydra_engine.documents.tokens import display_path, write_text
from hydra_engine.intake import approval_state as state_support
from hydra_engine.intake.classification import classify_migration_file
from hydra_engine.intake.inventory import migration_inventory
from hydra_engine.intake.ledger import markdown_cell, migration_ledger_text, migration_workspace_readme
from hydra_engine.intake.paths import IntakePaths
from hydra_engine.ports import clock as clock_port
from hydra_engine.ports import git as git_port


def apply_staging(paths: IntakePaths, state: dict) -> None:
    moves: list[tuple[Path, Path, dict]] = []
    for item in state["source_items"]:
        source = state_support.contained_relative(paths.root, item["source_path"], "source path")
        target = state_support.contained_relative(paths.root, item["planned_staged_path"], "staging target")
        state_support.assert_expected_staging_path(paths, state["slug"], item["route"], target)
        if not source.exists() or state_support.path_digest(source) != item["source_digest"]:
            raise ValueError(f"source drift detected before staging: {item['source_path']}")
        if target.exists():
            raise FileExistsError(f"staging target already exists: {item['planned_staged_path']}")
        moves.append((source, target, item))
    moved: list[tuple[Path, Path]] = []
    try:
        for source, target, item in moves:
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.move(str(source), str(target))
            moved.append((source, target))
            item["staged_path"] = display_path(target, paths.root)
            item["staged_digest"] = state_support.path_digest(target)
    except BaseException:
        for source, target in reversed(moved):
            if target.exists() and not source.exists():
                source.parent.mkdir(parents=True, exist_ok=True)
                shutil.move(str(target), str(source))
        raise

    workspace = state_support.batch_root(paths, state).parent.parent
    source = combined_staged_inventory(paths, state)
    readme = workspace / "README.md"
    ledger = workspace / "ledger.md"
    if not readme.exists():
        write_text(readme, migration_workspace_readme(state["slug"], source))
    if not ledger.exists():
        write_text(ledger, migration_ledger_text(state["slug"], source))
    state["phase"] = "staged"


def apply_publication(paths: IntakePaths, state: dict) -> None:
    proposal = state.get("proposal")
    validation = state.get("validation")
    if not proposal or not validation or validation["proposal_digest"] != proposal["proposal_digest"]:
        raise ValueError("publication requires matching independent validation evidence")
    if state_support.json_digest({key: value for key, value in proposal.items() if key != "proposal_digest"}) != proposal["proposal_digest"]:
        raise ValueError("proposal manifest drift detected before publication")
    writes: list[tuple[Path, str]] = []
    for unit in proposal["units"]:
        draft = state_support.contained_relative(paths.root, unit["draft_path"], "draft path")
        target = state_support.contained_relative(paths.root, unit["target_path"], "target path")
        if not draft.is_file() or state_support.path_digest(draft) != unit["draft_digest"]:
            raise ValueError(f"draft drift detected before publication: {unit['draft_path']}")
        current_target_digest = state_support.path_digest(target) if target.exists() else None
        if current_target_digest != unit["target_digest"]:
            raise ValueError(f"target drift detected before publication: {unit['target_path']}")
        try:
            content = draft.read_text(encoding="utf-8")
        except UnicodeDecodeError as error:
            raise ValueError(f"knowledge unit draft must be UTF-8 text: {unit['draft_path']}") from error
        writes.append((target, content))
    for target, content in writes:
        write_text(target, content)
    state["phase"] = "published"


def apply_closure(paths: IntakePaths, state: dict) -> None:
    reconciliation = state.get("reconciliation")
    if not reconciliation:
        raise ValueError("closure requires reconciliation evidence")
    removals: list[Path] = []
    for removal in reconciliation["removal_paths"]:
        path = state_support.contained_relative(paths.root, removal["path"], "staged removal path")
        if not path.exists() or state_support.path_digest(path) != removal["digest"]:
            raise ValueError(f"staged original drift detected before closure: {removal['path']}")
        removals.append(path)
    ledger_text = reconciled_ledger_text(state)
    for path in removals:
        if path.is_dir():
            shutil.rmtree(path)
        else:
            path.unlink()
    workspace = state_support.batch_root(paths, state).parent.parent
    write_text(workspace / "ledger.md", ledger_text)
    state["phase"] = "closed"


def inventory_sources(paths: IntakePaths, slug: str, sources: list[dict]) -> list[dict]:
    if not isinstance(sources, list):
        raise ValueError("sources must be a list")
    items: list[dict] = []
    destinations: set[str] = set()
    short_status = git_port.short_status(paths.root)
    for raw in sources:
        if not isinstance(raw, dict):
            raise ValueError("each source must be an object")
        route = raw.get("route")
        if route not in {"shared", "private"}:
            raise ValueError("source route must be `shared` or `private`")
        source = state_support.contained_relative(paths.root, str(raw.get("path", "")), "source path")
        if not source.exists():
            raise FileNotFoundError(f"migration source not found: {display_path(source, paths.root)}")
        if source.is_symlink():
            raise ValueError("migration source roots may not be symbolic links")
        base = paths.staging_root() / slug if route == "shared" else paths.root / ".hydra-framework.local/migrations" / slug / "originals"
        target = base / source.name
        target_rel = display_path(target, paths.root)
        if target_rel in destinations:
            raise ValueError(f"multiple sources map to the same staging target: {target_rel}")
        destinations.add(target_rel)
        if target.exists():
            raise FileExistsError(f"staging target already exists: {target_rel}")
        files = [source] if source.is_file() else sorted(path for path in source.rglob("*") if path.is_file())
        source_rel = display_path(source, paths.root)
        tracked = sorted(git_port.tracked_files(paths.root, source_rel))
        ignore_match = git_port.ignore_match(paths.root, source_rel)
        status_entries = [line for line in short_status if status_mentions(line, source_rel)]
        if tracked and len(tracked) == len(files):
            git_status = "tracked"
        elif ignore_match:
            git_status = "ignored"
        elif tracked:
            git_status = "mixed"
        elif status_entries and all(line[:2] == "??" for line in status_entries):
            git_status = "untracked"
        else:
            git_status = "unknown"
        findings = []
        all_tags: set[str] = set()
        size = 0
        for file in files:
            if file.is_symlink():
                raise ValueError("migration source trees may not contain symbolic links")
            tags = classify_migration_file(file, source if source.is_dir() else source.parent)
            all_tags.update(tags)
            file_size = file.stat().st_size
            size += file_size
            findings.append({"path": display_path(file, paths.root), "bytes": file_size, "classifications": tags})
        items.append(
            {
                "source_path": source_rel,
                "source_digest": state_support.path_digest(source),
                "route": route,
                "planned_staged_path": target_rel,
                "git": {
                    "status": git_status,
                    "tracked_files": tracked,
                    "ignore_match": ignore_match,
                    "status_entries": status_entries,
                },
                "files": len(files),
                "bytes": size,
                "classifications": sorted(all_tags),
                "findings": findings,
            }
        )
    return items


def combined_staged_inventory(paths: IntakePaths, state: dict) -> dict:
    shared = migration_inventory(paths, state["slug"])
    findings: list[dict] = []
    classifications: dict[str, int] = {}
    total_bytes = 0
    directories = 0
    if shared["sources"]:
        source = shared["sources"][0]
        findings.extend(source["findings"])
        total_bytes += source["bytes"]
        directories += source["directories"]
        for tag, count in source["classifications"].items():
            classifications[tag] = classifications.get(tag, 0) + count
    for item in state["source_items"]:
        if item["route"] != "private":
            continue
        root = state_support.contained_relative(paths.root, item["staged_path"], "private staged path")
        files = [root] if root.is_file() else sorted(path for path in root.rglob("*") if path.is_file())
        directories += 0 if root.is_file() else sum(1 for path in root.rglob("*") if path.is_dir())
        for file in files:
            tags = sorted(set(classify_migration_file(file, root if root.is_dir() else root.parent)) | {"private-hydra-risk"})
            size = file.stat().st_size
            total_bytes += size
            findings.append({"path": display_path(file, paths.root), "bytes": size, "classifications": tags})
            for tag in tags:
                classifications[tag] = classifications.get(tag, 0) + 1
    roots = [
        item["staged_path"] if item["route"] == "shared" else ".hydra-framework.local/migrations/<slug>/originals/"
        for item in state["source_items"]
    ]
    return {
        "path": ", ".join(roots),
        "files": len(findings),
        "directories": directories,
        "bytes": total_bytes,
        "classifications": dict(sorted(classifications.items())),
        "findings": sorted(findings, key=lambda finding: finding["path"]),
        "tracked_files": 0,
        "untracked_files": len(findings),
    }


def reconciled_ledger_text(state: dict) -> str:
    statuses = {row["path"]: row["status"] for row in state["reconciliation"]["items"]}
    destinations: dict[str, str] = {}
    for unit in (state.get("proposal") or {}).get("units", []):
        for source_item in unit["source_items"]:
            destinations[source_item] = unit["target_path"]
    routes = {finding["path"]: item["route"] for item in state["source_items"] for finding in item["findings"]}
    rows: list[list[str]] = []
    private_groups: dict[tuple[str, str], int] = {}
    for path in sorted(statuses):
        status = statuses[path]
        destination = destinations.get(path, "TBD")
        if status == "rejected":
            destination = "none"
        elif status == "kept-private":
            destination = ".hydra-framework.local/migrations/<slug>/originals/"
        if routes[path] == "private":
            key = (status, destination)
            private_groups[key] = private_groups.get(key, 0) + 1
            continue
        rows.append([f"`{path}`", status, f"`{destination}`", status, "reconciled by approved closure"])
    for (status, destination), count in sorted(private_groups.items()):
        rows.append([f"private staged items ({count})", status, f"`{destination}`", status, "grouped to avoid publishing private filenames"])
    row_lines = ["| Source | Verdict | Destination | Status | Notes |", "| --- | --- | --- | --- | --- |"]
    row_lines.extend("| " + " | ".join(markdown_cell(value) for value in row) + " |" for row in rows)
    return "\n".join(
        [
            f"# Migration Ledger: {state['slug']}", "", "Type: migration-ledger", "Status: complete",
            f"Updated: {clock_port.today()}", "", "Every source item in this bounded batch has a terminal status.", "",
            "## Status Values", "",
            "- `promoted`: durable meaning is under a canonical owner and the original is drained.",
            "- `kept-private`: the item received a private verdict; approved closure drained its staged original.",
            "- `rejected`: no durable meaning; recorded so nobody re-triages it.",
            "- `redirected`: the old authority is represented by a redirect to the new authority.", "",
            "## Ledger", "", *row_lines, "", "## Counts", "", f"- Total items: {len(statuses)}",
            f"- Terminal: {len(statuses)}", "- Pending: 0", "- Deferred: 0", "",
        ]
    )


def status_mentions(line: str, path: str) -> bool:
    status_path = line[3:].strip() if len(line) > 3 else ""
    return status_path == path or status_path.startswith(path.rstrip("/") + "/")
