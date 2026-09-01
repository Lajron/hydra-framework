"""Knowledge package routing (package-routing v2).

`context_terms` moved in from the deleted `knowledge.context_packs`:
route scoring is now the only caller, and this is where the
scoring lives.
"""

from __future__ import annotations

import re
import shlex
import shutil
from dataclasses import dataclass
from pathlib import Path

from hydra_engine.documents.tokens import HydraYamlError, cited_source_path_missing, display_path
from hydra_engine.documents.yaml_documents import parse_yaml, yaml_list, yaml_map, yaml_str
from hydra_engine.finding import Finding
from hydra_engine.identity.slugs import slugify
from hydra_engine.knowledge.packages import ContextCompilerPaths, discover_knowledge_packages
from hydra_engine.knowledge.units import units_by_id

ROUTING_SCHEMA = "hydra-framework.package-routing.v2"
MIN_CONTEXT_TERM_LENGTH = 2
MIN_PLURAL_STEM_LENGTH = 3
MIN_ROUTE_MATCH_SCORE = 2
MAX_ROUTED_PACKAGES = 3

# High-frequency English function words. A term-overlap-of-2 scorer treats
# any two shared words as a match, so common words the task and a route's
# `use_when` both happen to contain (e.g. "the") produced real false
# positives (F15: "fix the flaky login test" matched `fix_provider_surface`
# on `['fix', 'the']`). Not exhaustive -- just enough to stop generic words
# from carrying scoring weight.
STOPWORDS = frozenset({
    "the", "and", "for", "are", "was", "were", "with", "that", "this", "from",
    "have", "has", "had", "not", "but", "you", "your", "can", "will", "would",
    "should", "into", "about", "just", "then", "than", "also", "such", "some",
    "any", "all", "each", "more", "most", "other", "only", "own", "same",
    "too", "very", "use", "used", "using", "its", "our", "who", "what",
    "when", "where", "why", "how", "which", "there", "here", "been", "being",
    "does", "did", "doing", "yet", "get", "got", "one", "two",
})


def context_terms(text: str) -> set[str]:
    expanded = re.sub(r"([a-z0-9])([A-Z])", r"\1 \2", text)
    terms: set[str] = set()
    for term in re.findall(r"[a-z0-9]+", expanded.lower()):
        if len(term) <= MIN_CONTEXT_TERM_LENGTH or term in STOPWORDS:
            continue
        terms.add(term)
        if term.endswith("s") and len(term) > MIN_PLURAL_STEM_LENGTH:
            terms.add(term[:-1])
    return terms


def package_keyword_score(keywords: list[str], task_terms: frozenset[str]) -> float:
    """Proportion of `keywords` that share a `context_terms` token with
    `task_terms`, not a raw substring hit count (F: `hydra` matched
    `dehydrated`, and a package's score scaled with how many `keywords:`
    entries it listed rather than how well any of them fit the task -- a
    package could buy routing priority just by padding the list)."""
    if not keywords or not task_terms:
        return 0.0
    matched = sum(1 for keyword in keywords if context_terms(keyword) & task_terms)
    return matched / len(keywords)


def _rank_and_cap(
    scored: list[tuple[float, str, object]], cap: int,
) -> tuple[list[object], list[str], list[str]]:
    """Split `scored` (score, title, payload) triples into `(kept,
    capped_titles, ambiguous_titles)` against `cap` slots, highest score
    first. `title` only orders entries that are unambiguously kept or
    unambiguously dropped; it never decides which package holds the last
    slot when scores tie there (F: `route_prompt_package_pointers` broke
    that tie by spelling). A tie straddling the boundary drops every tied
    entry instead and is reported separately, so a caller can say the
    selection is ambiguous rather than silently guessing."""
    ordered = sorted(scored, key=lambda item: (-item[0], item[1]))
    if cap < 0 or len(ordered) <= cap:
        return [item[2] for item in ordered], [], []
    boundary_score = ordered[cap - 1][0]
    if ordered[cap][0] == boundary_score:
        ambiguous = [item[1] for item in ordered if item[0] == boundary_score]
        kept = [item[2] for item in ordered if item[0] > boundary_score]
        return kept, [], ambiguous
    return [item[2] for item in ordered[:cap]], [item[1] for item in ordered[cap:]], []


@dataclass(frozen=True)
class RoutePromptPointer:
    title: str
    state: str
    overview: str
    note: object
    route: str = ""
    priority_units: tuple[tuple[str, str], ...] = ()
    requires: tuple[tuple[str, str], ...] = ()
    avoid_by_default: tuple[str, ...] = ()


def read_package_routing(root: Path, paths: ContextCompilerPaths, resolver_paths: ObjectLocations) -> tuple[dict, str]:
    routing = root / "routing.yaml"
    try:
        data = parse_yaml(routing, resolver_paths.root)
    except HydraYamlError as error:
        return {}, str(error)
    if data and data.get("schema") != ROUTING_SCHEMA:
        return {}, f"{display_path(routing, paths.root)} schema is not `{ROUTING_SCHEMA}`"
    return data, ""


def _verify_command_unknown(entry: str, command_ids: tuple[str, ...]) -> bool:
    """Whether a route `verify:` entry names an `hydra.py` subcommand that
    is not actually registered (F16: a fabricated command was previously
    emitted to agents verbatim, un-caught by validation). Only entries that
    invoke `hydra.py` are checked; anything else (a test runner, a shell
    one-liner) is outside what this function can safely verify."""
    if not command_ids or "hydra.py" not in entry:
        return False
    match = re.search(r"hydra\.py\s+(\S+)(?:\s+(\S+))?", entry)
    if not match:
        return False
    first, second = match.group(1), match.group(2)
    if first in command_ids:
        return False
    if second and f"{first} {second}" in command_ids:
        return False
    return True


# Compound-command indicators (pipes, redirects, substitution, globs). A
# verify entry using any of these needs a real shell to interpret, so a
# naive first-token check would be unreliable -- skip rather than guess.
_SHELL_METACHARACTERS = frozenset("|&;()<>$`~*?{}[]\n")

# Shell builtins/keywords with no corresponding PATH executable. Without
# this list, a verify entry like `cd .. && pytest` would be flagged as
# "missing" for naming a builtin, not because anything is actually wrong.
_SHELL_BUILTINS = frozenset({
    "cd", "echo", "exit", "export", "eval", "exec", "source", ".", "test",
    "[", "pwd", "read", "true", "false", "printf", "set", "unset", "type",
    "alias", "wait", "trap",
})


def _verify_binary_missing(entry: str) -> bool:
    """Whether a non-`hydra.py` route `verify:` entry names a command whose
    binary cannot be found on PATH (slice 9 follow-up: that class of entry
    passed validation unchecked). Deliberately conservative -- this must
    never execute the command, only ask the shell's own lookup (`shutil.
    which`) whether it exists, so anything shaped like a compound command,
    a path, an env-var assignment, or a builtin is left unverified rather
    than risking a false positive."""
    if any(char in entry for char in _SHELL_METACHARACTERS):
        return False
    try:
        tokens = shlex.split(entry)
    except ValueError:
        return False
    if not tokens:
        return False
    first = tokens[0]
    if "/" in first or "=" in first or first in _SHELL_BUILTINS:
        return False
    return shutil.which(first) is None


def validate_routing_file(
    path: Path,
    paths: ContextCompilerPaths,
    resolver_paths: ObjectLocations,
    command_ids: tuple[str, ...] = (),
) -> list[Finding]:
    if not path.exists():
        return []
    try:
        data = parse_yaml(path, resolver_paths.root)
    except HydraYamlError as error:
        return [Finding(path=display_path(path, paths.root), code="routing-file", detail=str(error))]
    findings: list[Finding] = []
    label = display_path(path, paths.root)

    def add(detail: str) -> None:
        findings.append(Finding(path=label, code="routing-file", detail=detail))

    if data.get("schema") != ROUTING_SCHEMA:
        add(f"{label} schema must be `{ROUTING_SCHEMA}`")
    for key in ["package", "title", "keywords"]:
        if not data.get(key):
            add(f"{label} missing `{key}`")
    state = data.get("state")
    if state and not (paths.root / state).exists():
        add(f"{label} `state` target does not exist: {state}")

    for name, route in yaml_map(data.get("routes")).items():
        route_map = yaml_map(route)
        units_map = units_by_id(path.parent, paths.root)
        for key in ("priority_units", "requires"):
            for unit_id in yaml_list(route_map.get(key)):
                if unit_id not in units_map:
                    add(f"{label} route `{name}` `{key}` id does not resolve: {unit_id}")
        for entry in yaml_list(route_map.get("avoid_by_default")):
            if cited_source_path_missing(entry, path.parent, paths.root):
                add(f"{label} route `{name}` `avoid_by_default` path does not exist: {entry}")
        for entry in yaml_list(route_map.get("verify")):
            if _verify_command_unknown(entry, command_ids):
                add(f"{label} route `{name}` `verify` command is not a registered hydra.py command: {entry}")
            elif "hydra.py" not in entry and _verify_binary_missing(entry):
                add(f"{label} route `{name}` `verify` command binary not found on PATH: {entry}")
    return findings


def select_route(routing_data: dict, task: str) -> dict | None:
    """The best-scoring route for `task`, or `None` with no routes or below
    threshold. One scorer for the whole engine: the same name-plus-`use_when`
    term-overlap-of-at-least-2 rule the deleted context-pack matcher used."""
    routes = yaml_map(routing_data.get("routes"))
    if not routes:
        return None
    terms = context_terms(task)
    scored = []
    for name, route in routes.items():
        route_map = yaml_map(route)
        haystack = f"{name}\n" + "\n".join(yaml_list(route_map.get("use_when")))
        scored.append((len(terms & context_terms(haystack)), name, route_map))
    score, name, route_map = max(scored, key=lambda item: (item[0], item[1]))
    if score < MIN_ROUTE_MATCH_SCORE:
        return None
    return {"name": name, **route_map}


def resolve_named_route(routing_data: dict, name: str) -> dict | None:
    routes = yaml_map(routing_data.get("routes"))
    route = routes.get(name)
    if route is None:
        return None
    return {"name": name, **yaml_map(route)}


def route_packages(
    task: str,
    package_values: list[str],
    domain: str,
    paths: ContextCompilerPaths,
    resolver_paths: ObjectLocations,
    max_routed_packages: int = MAX_ROUTED_PACKAGES,
) -> tuple[list[dict], list[str]]:
    wanted = {slugify(value) for value in package_values if value}
    wanted_domain = slugify(domain) if domain else ""
    task_terms = frozenset(context_terms(task))
    selected: list[dict] = []
    # (score, title, item) for implicit keyword matches only -- an explicit
    # `--package`/`--domain` request is never ranked or capped, matching
    # `route_prompt_package_pointers`'s existing rule that a caller who named
    # exactly what it wants gets exactly that (F15's cap targeted this
    # display path only; this loading path was uncapped).
    scored_implicit: list[tuple[float, str, dict]] = []
    warnings: list[str] = []

    for root in discover_knowledge_packages(paths):
        data, warning = read_package_routing(root, paths, resolver_paths)
        if warning:
            warnings.append(f"Hydra routing skipped: {warning}")
            continue
        package = yaml_str(data.get("package"), root.name) if data else root.name
        title = yaml_str(data.get("title"), package)
        keywords = [item.lower() for item in yaml_list(data.get("keywords"))]
        package_slug = slugify(package)
        title_slug = slugify(title)
        item = {"root": root, "routing": data, "package": package, "title": title}
        if wanted and package_slug in wanted:
            selected.append({**item, "reason": "explicit package"})
        elif wanted_domain and wanted_domain in {package_slug, title_slug}:
            selected.append({**item, "reason": "explicit domain"})
        elif wanted_domain and any(wanted_domain == slugify(keyword) for keyword in keywords):
            selected.append({**item, "reason": "explicit domain keyword"})
        elif not wanted and not wanted_domain:
            score = package_keyword_score(keywords, task_terms)
            if score > 0:
                scored_implicit.append((score, title, {**item, "reason": "routing keyword"}))

    kept, capped, ambiguous = _rank_and_cap(scored_implicit, max_routed_packages)
    selected.extend(kept)
    if capped:
        warnings.append(
            f"{len(capped)} additional matching package(s) omitted "
            f"(showing the top {max_routed_packages} by keyword match); "
            "narrow with --package or --domain."
        )
    if ambiguous:
        warnings.append(
            f"Package selection is ambiguous at the top-{max_routed_packages} cutoff: "
            f"{', '.join(ambiguous)} tied on keyword match score; "
            "narrow with --package or --domain to pick one."
        )

    selected_slugs = {item["package"] for item in selected}
    for value in sorted(wanted - {slugify(item) for item in selected_slugs}):
        warnings.append(f"Package not found or not routable: {value}")

    if not selected and not wanted and not wanted_domain:
        packages = discover_knowledge_packages(paths)
        if len(packages) == 1:
            root = packages[0]
            data, warning = read_package_routing(root, paths, resolver_paths)
            if warning:
                warnings.append(f"Hydra routing skipped: {warning}")
            selected.append({
                "root": root,
                "routing": data,
                "package": yaml_str(data.get("package"), root.name) if data else root.name,
                "title": yaml_str(data.get("title"), root.name) if data else root.name,
                "reason": "only knowledge package available",
            })

    return selected, warnings


def route_prompt_package_pointers(
    prompt: str,
    paths: ContextCompilerPaths,
    resolver_paths: ObjectLocations,
    package_slugs: tuple[str, ...] = (),
    max_routed_packages: int = MAX_ROUTED_PACKAGES,
) -> tuple[list[RoutePromptPointer], list[str]]:
    task_terms = frozenset(context_terms(prompt))
    requested = {slugify(value) for value in package_slugs}
    # (match score, title, pointer) so an implicit multi-package match can be
    # ranked and capped (F15: an uncapped, unranked match set scales with
    # package count -- a synthetic 20-package tree injected all 20 blocks
    # into every prompt regardless of relevance). An explicit request
    # (`package_slugs`) is never ranked or capped: the caller already named
    # exactly what it wants.
    scored: list[tuple[float, str, RoutePromptPointer]] = []
    warnings: list[str] = []
    fallback: tuple[Path, dict] | None = None

    for root in discover_knowledge_packages(paths):
        data, warning = read_package_routing(root, paths, resolver_paths)
        if warning:
            warnings.append(warning)
            continue
        if not data:
            continue
        if fallback is None:
            fallback = (root, data)
        keywords = [item.lower() for item in yaml_list(data.get("keywords"))]
        package = yaml_str(data.get("package"), root.name)
        if requested and slugify(package) not in requested:
            continue
        score = package_keyword_score(keywords, task_terms)
        if not requested and score == 0:
            continue
        title = yaml_str(data.get("title"), package)
        state = yaml_str(data.get("state"), (root / "state.md").relative_to(paths.root).as_posix())
        overview = (root / "overview.md").relative_to(paths.root).as_posix()
        note = data.get("note", "Read package state and overview before broad repository search.")
        scored.append((score, title, RoutePromptPointer(
            title=title,
            state=state,
            overview=overview,
            note=note,
        )))

    if requested:
        matches = [pointer for _score, _title, pointer in scored]
    else:
        matches, capped, ambiguous = _rank_and_cap(scored, max_routed_packages)
        if capped:
            warnings.append(
                f"{len(capped)} additional matching package(s) omitted "
                f"(showing the top {max_routed_packages} by keyword match); "
                "narrow with --package or --domain, or run compile-context."
            )
        if ambiguous:
            warnings.append(
                f"Package selection is ambiguous at the top-{max_routed_packages} cutoff: "
                f"{', '.join(ambiguous)} tied on keyword match score; "
                "narrow with --package or --domain to pick one."
            )

    return matches, warnings


def package_routing_summary(data: dict, default_name: str) -> dict:
    """Package identity and collision-relevant fields out of a parsed
    `routing.yaml`, shared with `knowledge.routing_collisions` so that module
    does not need its own edge into `documents.yaml_documents` -- already a
    widely-imported vocabulary module at its architecture in-degree cap."""
    return {
        "package": yaml_str(data.get("package"), default_name),
        "title": yaml_str(data.get("title"), yaml_str(data.get("package"), default_name)),
        "team": yaml_map(data.get("owners")).get("team") or "unspecified",
        "keywords": {item.lower() for item in yaml_list(data.get("keywords"))},
        "routes": set(yaml_map(data.get("routes")).keys()),
    }
