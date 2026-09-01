"""Context/route provider registry (the context/route-provider
extension clause).

The engine architecture names context/route providers as an extension point a
downstream copy must be able to add without editing several central
switchboards. This closes that gap for object families: one
`ContextProvider` per family (`identity.object_families.OBJECT_FAMILIES`),
each contributing candidates to a `compile-context` packet.

Sequencing: the Knowledge provider first wraps the
existing knowledge-package routing/units logic verbatim -- the loop body
below is a straight move out of `knowledge.context_packets`, not a rewrite,
so a compile against an unchanged repository tree produces a byte-identical
packet. `rank` (from the shared search index) is added as a sort tiebreaker
alongside that move. The remaining five families -- Capability,
Work, Source, Runtime/Engine, Telemetry -- are genuinely new: each filters
the *same* search corpus by family rather than building its own, reusing
the existing search index rather than building a second corpus.

Registration is one tuple, `CONTEXT_PROVIDERS`, reviewed as code -- no
import-time scanning, no family contributes candidates merely because a
matching file exists on disk (the extension-registry rule).
"""

from __future__ import annotations

import dataclasses
from typing import Callable

from hydra_engine.documents.tokens import display_path
from hydra_engine.documents.yaml_documents import yaml_list, yaml_str
from hydra_engine.identity.object_families import family_for
from hydra_engine.identity.slugs import slugify
from hydra_engine.knowledge.candidates import add_candidate, file_candidate, resolve_context_path, unit_candidates
from hydra_engine.knowledge.routing import resolve_named_route, route_packages, select_route
from hydra_engine.knowledge.search_index import search as search_documents
from hydra_engine.knowledge.units import discover_unit_paths, read_unit, required_closure

# Priority band for every non-Knowledge provider's candidates: after explicit
# refs, package state/overview, and unit (+ reads) candidates, so a search
# match never displaces context a user or a package routed on purpose. One
# priority for all six families -- `rank` (below) is what orders within it.
PROVIDER_CANDIDATE_PRIORITY = 30

# How many candidates one non-Knowledge provider may contribute per compile,
# to bound blast radius. The Knowledge provider is uncapped here, matching
# its pre-existing, already-bounded-by-routing behavior; capping it too
# would change Part 1's byte-identical wrap into a behavior change.
DEFAULT_FAMILY_CANDIDATE_CAP = 8

# Search breadth used only to fill the five per-family caps above. Wider than
# `search_index.DEFAULT_RESULT_LIMIT` (20) because up to five unrelated
# families are being filtered out of one ranked list; too small a pool would
# starve a family whose best matches rank outside the top 20 overall.
PROVIDER_SEARCH_RESULT_LIMIT = 200

KNOWLEDGE_FAMILY = "Knowledge"
SEARCH_FAMILIES = ("Capability", "Work", "Source", "Runtime/Engine", "Telemetry")

# Moved from `context_packets` (Part 1 wrap): package-level candidate
# priorities the Knowledge provider still emits.
PACKAGE_STATE_PRIORITY = 10
PACKAGE_OVERVIEW_PRIORITY = 20


@dataclasses.dataclass(frozen=True)
class ProviderRequest:
    # `paths`/`resolver_paths` are `ContextCompilerPaths`/`ObjectLocations`
    # (matching `context_packets.compile_context_packet`'s own hints):
    # named here, not imported, since `from __future__ import annotations`
    # never evaluates them and importing either would push this module's
    # fan-out past what the Knowledge-provider move already needs.
    task: str
    paths: "ContextCompilerPaths"
    resolver_paths: "ObjectLocations"
    object_seed_ids: frozenset
    chars_per_token: int
    family_cap: int
    package_values: tuple[str, ...] = ()
    domain: str = ""
    search_results: tuple = ()
    route_values: tuple[str, ...] = ()
    command_ids: tuple[str, ...] = ()


@dataclasses.dataclass(frozen=True)
class ProviderOutput:
    candidates: list[dict] = dataclasses.field(default_factory=list)
    packages: list[dict] = dataclasses.field(default_factory=list)
    avoid_by_default: list[str] = dataclasses.field(default_factory=list)
    verify: list[str] = dataclasses.field(default_factory=list)
    warnings: list[str] = dataclasses.field(default_factory=list)


@dataclasses.dataclass(frozen=True)
class ContextProvider:
    family: str
    collect: Callable[["ProviderRequest"], ProviderOutput]


def _collect_knowledge(request: ProviderRequest) -> ProviderOutput:
    """Everything `compile_context_packet`'s package-routing loop did before
    Part 5 -- moved, not rewritten. See this module's docstring for why that
    distinction matters here."""
    routed, warnings = route_packages(request.task, list(request.package_values), request.domain, request.paths, request.resolver_paths)
    candidates: list[dict] = []
    seen: set[str] = set()
    packages_out: list[dict] = []
    avoid_by_default: list[str] = []
    verify_commands: list[str] = []
    route_requests = _route_requests_by_package(request.route_values, warnings)
    selected_package_slugs: set[str] = set()

    for item in routed:
        root = item["root"]
        data = item["routing"]
        package_slug = slugify(item["package"])
        selected_package_slugs.add(package_slug)
        defaults = {
            "state": (root / "state.md").relative_to(request.paths.root).as_posix(),
            "overview": (root / "overview.md").relative_to(request.paths.root).as_posix(),
        }
        for key, priority in [("state", PACKAGE_STATE_PRIORITY), ("overview", PACKAGE_OVERVIEW_PRIORITY)]:
            raw_path = yaml_str(data.get(key), defaults[key])
            path = resolve_context_path(raw_path, request.paths)
            if path.exists() and path.is_file():
                add_candidate(candidates, seen, file_candidate(
                    path,
                    kind=f"package-{key.replace('_', '-')}",
                    reason=f"{item['package']} {item['reason']}",
                    priority=priority,
                    paths=request.paths,
                    source=item["package"],
                    chars_per_token=request.chars_per_token,
                ))

        units = [u for p in discover_unit_paths(root) if (u := read_unit(p, request.paths.root))]
        units_map = {u.hydra_id.lower(): u for u in units if u.hydra_id}
        explicit_route_names = route_requests.get(package_slug, [])
        active_routes: list[dict] = []
        for route_name in explicit_route_names:
            route = resolve_named_route(data, route_name)
            if route is None:
                warnings.append(f"Route not found in package {item['package']}: {route_name}")
            else:
                active_routes.append(route)

        if not explicit_route_names:
            auto_route = select_route(data, request.task)
            if auto_route is not None:
                active_routes.append(auto_route)

        route_names: list[str] = []
        rank_by_unit_id: dict[str, float] = {}
        if active_routes:
            route_required_ids = {ref.lower() for route in active_routes for ref in yaml_list(route.get("requires"))}
            seed_ids = set(request.object_seed_ids) | route_required_ids
            item_required_ids = required_closure(units_map, seed_ids, warnings)
            # A route narrows a package's units to the ones it names, rather
            # than every unit the package has ever accumulated -- that
            # narrowing is the whole point of a route existing.
            candidate_ids = {
                unit_id.lower()
                for route in active_routes
                for unit_id in yaml_list(route.get("priority_units"))
            } | item_required_ids
            route_units = [u for u in units if u.hydra_id.lower() in candidate_ids]
            for route in active_routes:
                route_names.append(yaml_str(route.get("name")))
                for value in yaml_list(route.get("avoid_by_default")):
                    if value not in avoid_by_default:
                        avoid_by_default.append(value)
                for value in yaml_list(route.get("verify")):
                    if value not in verify_commands:
                        verify_commands.append(value)
        else:
            item_required_ids = required_closure(units_map, set(request.object_seed_ids), warnings)
            route_units, rank_by_unit_id = _rank_no_route_units(root, units, item_required_ids, request)

        for candidate in unit_candidates(
            route_units,
            package=item["package"],
            paths=request.paths,
            required_ids=item_required_ids,
            warnings=warnings,
            chars_per_token=request.chars_per_token,
        ):
            rank = rank_by_unit_id.get(str(candidate.get("source", "")).lower())
            if rank is not None:
                candidate["rank"] = rank
            add_candidate(candidates, seen, candidate)

        packages_out.append({
            "package": item["package"], "title": item["title"], "reason": item["reason"],
            "route": ", ".join(name for name in route_names if name),
        })

    for package_slug, route_names in route_requests.items():
        if package_slug not in selected_package_slugs:
            warnings.append(f"Route package not selected: {package_slug}:{', '.join(route_names)}")

    return ProviderOutput(candidates=candidates, packages=packages_out, avoid_by_default=avoid_by_default, verify=verify_commands, warnings=warnings)


def _route_requests_by_package(route_values: tuple[str, ...], warnings: list[str]) -> dict[str, list[str]]:
    requests: dict[str, list[str]] = {}
    for value in route_values:
        if ":" not in value:
            warnings.append(f"Route must be package-qualified as <package>:<route>: {value}")
            continue
        package, route = value.split(":", 1)
        package_slug = slugify(package.strip())
        route_name = route.strip()
        if not package_slug or not route_name:
            warnings.append(f"Route must be package-qualified as <package>:<route>: {value}")
            continue
        requests.setdefault(package_slug, []).append(route_name)
    return requests


def _rank_no_route_units(root, units, required_ids: set[str], request: ProviderRequest) -> tuple[list, dict[str, float]]:
    by_path = {display_path(unit.path, request.paths.root): unit for unit in units}
    by_id = {unit.hydra_id.lower(): unit for unit in units if unit.hydra_id}
    selected: list = []
    seen: set[str] = set()
    rank_by_unit_id: dict[str, float] = {}

    for unit in units:
        if unit.hydra_id.lower() in required_ids:
            selected.append(unit)
            seen.add(unit.hydra_id.lower())

    optional_count = 0
    for result in request.search_results:
        doc = result.document
        unit = by_id.get(doc.hydra_id.lower()) if doc.hydra_id else None
        if unit is None and doc.path:
            unit = by_path.get(doc.path)
        if unit is None:
            continue
        unit_id = unit.hydra_id.lower()
        if unit_id in seen:
            continue
        if request.family_cap >= 0 and optional_count >= request.family_cap:
            break
        selected.append(unit)
        seen.add(unit_id)
        rank_by_unit_id[unit_id] = result.rank
        optional_count += 1

    return selected, rank_by_unit_id


def _family_search_collector(family: str):
    def _collect(request: ProviderRequest) -> ProviderOutput:
        candidates: list[dict] = []
        seen_paths: set[str] = set()
        for result in request.search_results:
            doc = result.document
            if not doc.path or doc.path in seen_paths:
                continue
            if family_for(doc.hydra_id, doc.kind) != family:
                continue
            path = resolve_context_path(doc.path, request.paths)
            if not path.exists() or not path.is_file():
                continue
            seen_paths.add(doc.path)
            candidate = file_candidate(
                path,
                kind=f"context-provider-{slugify(family)}",
                reason=f"{family} context provider match" + (f" for {request.task!r}" if request.task else ""),
                priority=PROVIDER_CANDIDATE_PRIORITY,
                paths=request.paths,
                source=doc.hydra_id,
                chars_per_token=request.chars_per_token,
            )
            candidate["rank"] = result.rank
            candidates.append(candidate)
            if len(candidates) >= request.family_cap:
                break
        return ProviderOutput(candidates=candidates)

    return _collect


CONTEXT_PROVIDERS: tuple[ContextProvider, ...] = (
    ContextProvider(KNOWLEDGE_FAMILY, _collect_knowledge),
    *(ContextProvider(family, _family_search_collector(family)) for family in SEARCH_FAMILIES),
)
PROVIDERS_BY_FAMILY: dict[str, ContextProvider] = {provider.family: provider for provider in CONTEXT_PROVIDERS}


def _matched_families(values: tuple[str, ...]) -> tuple[set[str], list[str]]:
    """Which registered families `values` names (matched by slug, so
    `--include-family runtime-engine` and `--include-family Runtime/Engine`
    both resolve to the `Runtime/Engine` provider), plus the values that
    matched nothing."""
    matched: set[str] = set()
    unknown: list[str] = []
    for value in values:
        hit = next((family for family in PROVIDERS_BY_FAMILY if slugify(value) == slugify(family)), None)
        if hit is None:
            unknown.append(value)
        else:
            matched.add(hit)
    return matched, unknown


def run_context_providers(
    request: ProviderRequest,
    *,
    include_families: tuple[str, ...] = (),
    exclude_families: tuple[str, ...] = (),
) -> ProviderOutput:
    """Run every active provider and merge their candidates into one
    dedup pass, in `CONTEXT_PROVIDERS` registration order (Knowledge first).

    `include_families` narrows to exactly the named families;
    `exclude_families` drops named families from whatever set would
    otherwise run. Both are family include/exclude blast-
    radius controls alongside the per-family cap on `request.family_cap`.
    """
    warnings: list[str] = []
    included, unknown_included = _matched_families(include_families)
    excluded, unknown_excluded = _matched_families(exclude_families)
    for value in [*unknown_included, *unknown_excluded]:
        warnings.append(f"Unknown context-provider family: {value}")

    active = [
        family for family in PROVIDERS_BY_FAMILY
        if (family in included if include_families else True) and family not in excluded
    ]

    if active:
        results, _features, _source = search_documents(
            request.task,
            paths=request.paths,
            resolver_paths=request.resolver_paths,
            local=request.resolver_paths.local,
            command_ids=request.command_ids,
            limit=PROVIDER_SEARCH_RESULT_LIMIT,
        )
        request = dataclasses.replace(request, search_results=tuple(results))

    candidates: list[dict] = []
    seen: set[str] = set()
    packages_out: list[dict] = []
    avoid_by_default: list[str] = []
    verify_commands: list[str] = []

    for family in active:
        output = PROVIDERS_BY_FAMILY[family].collect(request)
        for candidate in output.candidates:
            add_candidate(candidates, seen, candidate)
        packages_out.extend(output.packages)
        for value in output.avoid_by_default:
            if value not in avoid_by_default:
                avoid_by_default.append(value)
        for value in output.verify:
            if value not in verify_commands:
                verify_commands.append(value)
        warnings.extend(output.warnings)

    return ProviderOutput(
        candidates=candidates, packages=packages_out, avoid_by_default=avoid_by_default,
        verify=verify_commands, warnings=warnings,
    )
