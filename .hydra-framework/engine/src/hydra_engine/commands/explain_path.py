"""explain-path command implementation.

Read-only ownership derivation, composed entirely from sources that already
exist: object lookup by path and its own state tier, family, relations, and
provenance (`objects.envelopes`/`objects.store_queries`, and the full-tree
scan via `objects.registry.scan_objects` -- a thin re-export of
`objects.discovery.collect_hydra_objects`, since that module already sits at
architecture check 4's in-degree cap and cannot take an eleventh direct
importer), reverse citations both by relation (`store_queries.citers_of`,
mirrored here for the scan path) and by provenance source (`store_queries.
citers_of_source_path`, new alongside it), and provider adapter planning and
sidecar logic (`providers.reclaim.classify_surfaces`). The only new registry
is `identity.path_owners`, for the two shapes that carry no object envelope:
a directory, and a hand-maintained provider-root file.

Store-backed when the operational store is fresh, the same contract
`commands.references` follows, scan-backed otherwise -- never
a hard requirement on the store, unlike `ref rdeps`/`ref impact`, because
`explain-path` must stay useful on a repository that has never run
`ref store rebuild`.
"""

from __future__ import annotations

import json
from pathlib import Path

from hydra_engine.commands import CommandResult
from hydra_engine.documents.tokens import expand_brace_sets
from hydra_engine.identity import path_owners
from hydra_engine.objects.envelopes import object_display_path, object_state_tier, resolved_envelope_path
from hydra_engine.objects.registry import scan_objects
from hydra_engine.objects import store_queries
from hydra_engine.providers.reclaim import classify_surfaces

EXPLAIN_PATH_SCHEMA = "hydra-framework.explain-path.v1"
PROVIDER_ROOT_PREFIXES = (".claude", ".codex", ".agents")


def _resolve_target(raw: str, root: Path) -> Path:
    candidate = Path(raw)
    return candidate if candidate.is_absolute() else root / candidate


def _normalize_object(obj: dict) -> dict:
    return {
        "id": obj.get("id") or obj.get("hydra_id"),
        "family": obj["family"],
        "kind": obj["kind"],
        "title": obj["title"],
        "status": obj["status"],
        "scope": obj["scope"],
        "tier": obj["tier"],
        "aliases": obj["aliases"],
        "relations": obj["relations"],
        "provenance_sources": obj["provenance_sources"],
    }


def _provenance_source_matches(raw: str, citation_dir: Path, repo_root: Path, target: Path) -> bool:
    base = citation_dir if raw.startswith("./") or raw.startswith("../") else repo_root
    for candidate in expand_brace_sets(raw):
        candidate = candidate.rstrip("/")
        if not candidate:
            continue
        if "*" in candidate:
            if any(found.resolve() == target for found in base.glob(candidate)):
                return True
            continue
        if (base / candidate).resolve() == target:
            return True
    return False


def _scan_provenance_citers(objects: list[dict], resolver_paths, target: Path) -> list[str]:
    citers: set[str] = set()
    for obj in objects:
        citation_dir = resolved_envelope_path(obj["envelope_path"], resolver_paths).parent
        for raw in obj["provenance_sources"]:
            if _provenance_source_matches(raw, citation_dir, resolver_paths.root, target):
                citers.add(obj["id"])
                break
    return sorted(citers)


def _provider_surface(rel: str, providers_paths) -> dict | None:
    if not any(rel == prefix or rel.startswith(f"{prefix}/") for prefix in PROVIDER_ROOT_PREFIXES):
        return None
    for item in classify_surfaces(providers_paths):
        if item["path"] == rel:
            return {"status": item["status"], "kind": item["kind"], "detail": item["detail"]}
    declared = path_owners.provider_root_declaration(rel)
    if declared is not None:
        return {"status": declared.status, "kind": "", "detail": declared.detail}
    return {"status": "unclassified", "kind": "", "detail": "under a provider root with no generated-surface or ownership declaration match"}


def _store_lookup(conn, display: str) -> tuple[dict | None, list[str], list[str]]:
    """`(object, reverse_citations, notes)` from the operational store."""
    matches = store_queries.by_path(conn, display)
    unique_ids = sorted({row["hydra_id"] for row in matches})
    if len(unique_ids) > 1:
        return None, [], [f"ambiguous object path: {', '.join(unique_ids)}"]
    if not unique_ids:
        return None, [], []
    obj = store_queries.resolve(conn, unique_ids[0])
    return obj, store_queries.citers_of(conn, unique_ids[0]), []


def _scan_lookup(objects: list[dict], display: str) -> tuple[dict | None, list[str], list[str]]:
    """`(object, reverse_citations, notes)` from a full-tree scan."""
    matches = [obj for obj in objects if obj["path"] == display]
    if len(matches) > 1:
        return None, [], [f"ambiguous object path: {', '.join(sorted(obj['id'] for obj in matches))}"]
    if not matches:
        return None, [], []
    obj = matches[0]
    reverse_citations = sorted({other["id"] for other in objects if obj["id"] in other["relations"]})
    return obj, reverse_citations, []


def explain_path(raw_path: str, ctx) -> dict:
    resolver_paths = ctx.resolver_paths()
    target = _resolve_target(raw_path, ctx.root)
    display = object_display_path(target, resolver_paths)
    tier = object_state_tier(target, resolver_paths)

    conn = store_queries.open_fresh_store(resolver_paths, resolver_paths.local)
    if conn is not None:
        try:
            source = "sqlite"
            obj, reverse_citations, notes = _store_lookup(conn, display)
            provenance_citers = store_queries.citers_of_source_path(conn, display)
        finally:
            conn.close()
    else:
        source = "scan"
        objects, errors = scan_objects(resolver_paths)
        obj, reverse_citations, notes = _scan_lookup(objects, display)
        notes = list(notes) + list(errors)
        provenance_citers = _scan_provenance_citers(objects, resolver_paths, target.resolve())

    directory_owner = (
        path_owners.directory_owner(display.removeprefix(".hydra-framework/"))
        if display.startswith(".hydra-framework/") else None
    )

    return {
        "schema": EXPLAIN_PATH_SCHEMA,
        "path": display,
        "exists": target.exists(),
        "tier": tier,
        "source": source,
        "object": _normalize_object(obj) if obj else None,
        "reverse_citations": reverse_citations,
        "provenance_citers": provenance_citers,
        "directory_owner": directory_owner,
        "provider_surface": _provider_surface(display, ctx.providers_paths()),
        "notes": notes,
    }


def _print_report(report: dict) -> None:
    print("Hydra explain-path")
    print(f"Path: {report['path']}")
    print(f"Exists: {report['exists']}")
    print(f"Tier: {report['tier']}")
    print(f"Source: {report['source']}")
    obj = report["object"]
    if obj:
        print(f"Object: {obj['id']} ({obj['family']}/{obj['kind']})")
        print(f"  status: {obj['status']}, scope: {obj['scope']}, title: {obj['title']}")
        if obj["aliases"]:
            print(f"  aliases: {', '.join(obj['aliases'])}")
        if obj["relations"]:
            print(f"  relations: {', '.join(obj['relations'])}")
        if obj["provenance_sources"]:
            print(f"  provenance_sources: {', '.join(obj['provenance_sources'])}")
    else:
        print("Object: none")
    if report["reverse_citations"]:
        print("Reverse citations:")
        for citer in report["reverse_citations"]:
            print(f"- {citer}")
    if report["provenance_citers"]:
        print("Cited as provenance by:")
        for citer in report["provenance_citers"]:
            print(f"- {citer}")
    if report["directory_owner"]:
        print(f"Directory owner: {report['directory_owner']}")
    surface = report["provider_surface"]
    if surface:
        print(f"Provider surface: {surface['status']}")
        if surface["detail"]:
            print(f"  {surface['detail']}")
    for note in report["notes"]:
        print(f"Note: {note}")


def command_explain_path(args, ctx) -> CommandResult:
    report = explain_path(args.path, ctx)
    if args.json:
        print(json.dumps(report, indent=2))
    else:
        _print_report(report)
    return CommandResult(0)


def register(subparsers) -> None:
    explain = subparsers.add_parser("explain-path", help="Derive what owns a repository path")
    explain.add_argument("path", help="File or directory path, absolute or relative to the repository root")
    explain.add_argument("--json", action="store_true", help="Emit machine-readable output")
    explain.set_defaults(func=_dispatch_explain_path)


def _dispatch_explain_path(args, ctx) -> int:
    return command_explain_path(args, ctx).exit_code
