"""Per-package match detail for `route-prompt --json` (Hydra routing
authority task, Governance and observability).

Split out of `knowledge.routing` rather than added there: that module sits
at the architecture module-size cap, and `route_prompt_package_pointers`
deliberately does not carry a package's match score on `RoutePromptPointer`
-- the plain-text hook output is kept to pointers and exact
references only, so this score/reason detail must live somewhere that can
never be printed by that path. `--json` is a separate, explicit diagnostic
invocation, so it is safe here. Reads `package`/`title`/`keywords` through
`routing.package_routing_summary` rather than `documents.yaml_documents`
directly, matching `knowledge.routing_collisions`'s precedent: that module
is already a widely-imported vocabulary module at its architecture
in-degree cap.
"""

from __future__ import annotations

from hydra_engine.identity.slugs import slugify
from hydra_engine.knowledge.packages import ContextCompilerPaths, discover_knowledge_packages
from hydra_engine.knowledge.routing import context_terms, package_keyword_score, package_routing_summary, read_package_routing


def route_prompt_match_diagnostics(
    prompt: str,
    paths: ContextCompilerPaths,
    resolver_paths: "ObjectLocations",
    package_slugs: tuple[str, ...] = (),
) -> list[dict]:
    """`{package, title, score}` for every package `route_prompt_package_pointers`
    would consider a candidate for the same `prompt`/`package_slugs` -- a
    superset of what it actually renders, since this does not repeat that
    function's rank-and-cap step. Callers filter to the titles that function
    actually matched before showing scores for them."""
    task_terms = frozenset(context_terms(prompt))
    requested = {slugify(value) for value in package_slugs}
    entries: list[dict] = []
    for root in discover_knowledge_packages(paths):
        data, warning = read_package_routing(root, paths, resolver_paths)
        if warning or not data:
            continue
        summary = package_routing_summary(data, root.name)
        if requested and slugify(summary["package"]) not in requested:
            continue
        score = package_keyword_score(list(summary["keywords"]), task_terms)
        if not requested and score == 0:
            continue
        entries.append({"package": summary["package"], "title": summary["title"], "score": round(score, 4)})
    return entries
