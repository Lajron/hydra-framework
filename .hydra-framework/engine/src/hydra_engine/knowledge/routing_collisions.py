"""Cross-package `routing.yaml` collision validation: the multi-package
merge gate.

Split out of `knowledge.routing` rather than added there: that module sits
at the architecture module-size cap, and this check reads every package's
routing file at once rather than one at a time like the rest of that module.
"""

from __future__ import annotations

from hydra_engine.documents.tokens import display_path
from hydra_engine.finding import Finding
from hydra_engine.knowledge.packages import discover_knowledge_packages
from hydra_engine.knowledge.routing import package_routing_summary, read_package_routing


def validate_package_routing_collisions(
    paths: "ContextCompilerPaths",
    resolver_paths: "ObjectLocations",
) -> list[Finding]:
    """Cross-package `routing.yaml` collisions `validate_routing_file` cannot
    see, since it only ever reads one file at a time: the same keyword or the
    same route name declared by two packages. Every package selects and
    activates independently, so a shared keyword silently inflates a
    package's implicit routing score, and a shared route name is only safe
    today because every interface requires a package-qualified reference --
    a future bare-name interface would not be. Findings
    name both packages' owning teams (`owners.team`) rather than looking one
    up in a maintained roster."""
    entries: list[dict] = []
    for root in discover_knowledge_packages(paths):
        data, warning = read_package_routing(root, paths, resolver_paths)
        if warning or not data:
            continue
        entries.append({
            "path": display_path(root / "routing.yaml", paths.root),
            **package_routing_summary(data, root.name),
        })

    def label(entry: dict) -> str:
        return f"{entry['package']} (owned by {entry['team']})"

    findings: list[Finding] = []
    for index, first in enumerate(entries):
        for second in entries[index + 1:]:
            for keyword in sorted(first["keywords"] & second["keywords"]):
                findings.append(Finding(
                    path=first["path"], code="routing-collision",
                    detail=f"keyword `{keyword}` is declared by both {label(first)} and {label(second)}",
                ))
            for route in sorted(first["routes"] & second["routes"]):
                findings.append(Finding(
                    path=first["path"], code="routing-collision",
                    detail=f"route `{route}` is declared by both {label(first)} and {label(second)}",
                ))
    return findings
