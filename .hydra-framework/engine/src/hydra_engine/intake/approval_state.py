"""Persistence, digest, and trust-boundary helpers for migration approvals."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

from hydra_engine import config
from hydra_engine.documents.tokens import display_path, is_relative_to, write_text
from hydra_engine.intake.ledger import migration_workspace_matches
from hydra_engine.intake.paths import IntakePaths
from hydra_engine.intake.staging import validate_migration_slug
from hydra_engine.ports import clock as clock_port

APPROVAL_SCHEMA = "hydra-framework.migration-approval.v1"
OUTCOMES = frozenset({"approve", "reject", "revise"})
TERMINAL_LEDGER_STATUSES = frozenset({"promoted", "redirected", "rejected", "kept-private"})
RISK_CLASSIFICATIONS = frozenset(
    {"credential-or-private-risk", "machine-local-risk", "private-hydra-risk"}
)
AMBIGUOUS_CLASSIFICATIONS = frozenset({"source-material", "task-or-session-state"})
FORBIDDEN_WORKER_KEYS = frozenset({"provider", "model", "vendor"})


def load_batch(paths: IntakePaths, slug: str, batch: str) -> dict:
    slug, batch = slugs(slug, batch)
    path = state_path(paths, slug, batch)
    if not path.is_file():
        raise FileNotFoundError(f"migration batch not found: {batch}")
    state = json.loads(path.read_text(encoding="utf-8"))
    if state.get("schema") != APPROVAL_SCHEMA or state.get("slug") != slug or state.get("batch") != batch:
        raise ValueError(f"invalid migration approval state: {display_path(path, paths.root)}")
    return state


def normalize_reconciliation(value: object) -> dict[str, str]:
    if isinstance(value, dict):
        if "items" in value:
            value = value["items"]
        else:
            if any(not isinstance(key, str) or not isinstance(status, str) for key, status in value.items()):
                raise ValueError("reconciliation mapping must contain string paths and statuses")
            return dict(value)
    if not isinstance(value, list):
        raise ValueError("reconciliation must be a path-to-status mapping or item list")
    rows: dict[str, str] = {}
    for row in value:
        if not isinstance(row, dict) or not isinstance(row.get("path"), str) or not isinstance(row.get("status"), str):
            raise ValueError("each reconciliation item needs string path and status fields")
        if row["path"] in rows:
            raise ValueError(f"duplicate reconciliation item: {row['path']}")
        rows[row["path"]] = row["status"]
    return rows


def validate_drafting_chain(value: object, *, default_capability_class: str = "") -> list[dict]:
    if not isinstance(value, list) or not value:
        raise ValueError("drafting_chain must be a non-empty list")
    chain: list[dict] = []
    seen: set[str] = set()
    for entry in value:
        if isinstance(entry, str):
            entry = {"instance": entry, "capability_class": default_capability_class}
        if not isinstance(entry, dict):
            raise ValueError("drafting_chain entries must be instance strings or objects")
        reject_provider_specific_keys(entry)
        instance = str(entry.get("instance", "")).strip()
        capability_class = str(entry.get("capability_class", ""))
        if not instance or instance in seen:
            raise ValueError("drafting_chain instance identifiers must be non-empty and unique")
        validate_capability_class(capability_class)
        seen.add(instance)
        chain.append({"instance": instance, "capability_class": capability_class})
    return chain


def validate_capability_class(value: str) -> None:
    if value not in config.CAPABILITY_CLASSES:
        raise ValueError(f"unknown capability class `{value}`")


def reject_provider_specific_keys(value: object) -> None:
    if isinstance(value, dict):
        forbidden = sorted(str(key) for key in value if str(key).lower() in FORBIDDEN_WORKER_KEYS)
        if forbidden:
            raise ValueError(f"provider-neutral manifests may not use keys: {', '.join(forbidden)}")
        for nested in value.values():
            reject_provider_specific_keys(nested)
    elif isinstance(value, list):
        for nested in value:
            reject_provider_specific_keys(nested)


def contained_relative(root: Path, value: str, label: str) -> Path:
    candidate = Path(value)
    if not value or candidate.is_absolute() or ".." in candidate.parts:
        raise ValueError(f"{label} must be a root-contained relative path")
    resolved = root / candidate
    if not is_relative_to(resolved, root):
        raise ValueError(f"{label} must stay within the repository root")
    return resolved


def assert_expected_staging_path(paths: IntakePaths, slug: str, route: str, path: Path) -> None:
    expected = paths.staging_root() / slug if route == "shared" else paths.root / ".hydra-framework.local/migrations" / slug / "originals"
    if not is_relative_to(path, expected) or path == expected:
        raise ValueError("staged path is outside its approved route")


def path_digest(path: Path) -> str:
    if path.is_symlink():
        raise ValueError(f"cannot digest symbolic link: {path}")
    digest = hashlib.sha256()
    if path.is_file():
        digest.update(b"file\0")
        digest.update(path.read_bytes())
        return digest.hexdigest()
    if not path.is_dir():
        raise FileNotFoundError(path)
    digest.update(b"directory\0")
    for child in sorted(path.rglob("*")):
        if child.is_symlink():
            raise ValueError(f"cannot digest symbolic link: {child}")
        rel = child.relative_to(path).as_posix().encode()
        digest.update(b"dir\0" if child.is_dir() else b"file\0")
        digest.update(rel)
        digest.update(b"\0")
        if child.is_file():
            digest.update(child.read_bytes())
    return digest.hexdigest()


def json_digest(value: object) -> str:
    encoded = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()
    return hashlib.sha256(encoded).hexdigest()


def gate(kind: str, revision: int, reasons: list[str], action: dict) -> dict:
    return {
        "kind": kind,
        "status": "pending",
        "revision": revision,
        "reasons": list(dict.fromkeys(reasons)),
        "action": action,
    }


def slugs(slug: str, batch: str) -> tuple[str, str]:
    return validate_migration_slug(slug), validate_migration_slug(batch)


def workspace(paths: IntakePaths, slug: str, batch: str, *, existing: dict | None = None) -> Path:
    if existing:
        return contained_relative(paths.root, existing["workspace"], "workspace path")
    matches = [path for path in migration_workspace_matches(paths, slug) if (path / "batches" / batch / "state.json").is_file()]
    if len(matches) > 1:
        raise ValueError(f"multiple migration workspaces contain batch `{batch}`")
    return matches[0] if matches else paths.workspace_root() / f"{clock_port.today()}-{slug}"


def batch_root(paths: IntakePaths, state: dict) -> Path:
    return contained_relative(paths.root, state["workspace"], "workspace path") / "batches" / state["batch"]


def state_path(paths: IntakePaths, slug: str, batch: str) -> Path:
    return workspace(paths, slug, batch) / "batches" / batch / "state.json"


def load_optional(paths: IntakePaths, slug: str, batch: str) -> dict | None:
    path = state_path(paths, slug, batch)
    return load_batch(paths, slug, batch) if path.is_file() else None


def save(paths: IntakePaths, state: dict) -> None:
    write_text(batch_root(paths, state) / "state.json", json_text(state))


def json_text(value: object) -> str:
    return json.dumps(value, indent=2, sort_keys=True, ensure_ascii=False) + "\n"
