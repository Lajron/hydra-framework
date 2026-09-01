"""Path-owner registry for `explain-path`.

Every other source `explain-path` composes already exists: an object's own
envelope answers ownership for files that declare one. This registry answers
for the two shapes that never carry an envelope -- a directory (`core/`,
`scripts/`, ...) and a provider-root file that is hand-maintained rather than
generated (`.claude/settings.json`, `.claude/rules/`).

Boring data plus two lookup functions, following the established
pattern (`identity.object_families`, `objects.object_handlers`): explicit
tuples reviewed as code, not a hand-authored YAML file that can drift from
what is actually true, and not import-time discovery of anything.

`HYDRA_DIRECTORY_OWNERS` mirrors `core/ownership-and-composition.md`'s
"Responsibility Ownership" section -- prose an agent reads, but not
something `explain-path` could introspect from the tree itself. It is
supplementary context, not exclusive of object-level detail: a path can
resolve as an object *and* match a directory owner.

`PROVIDER_ROOT_DECLARATIONS` mirrors what `CLAUDE.md`/`AGENTS.md` state
about `.claude/`: `providers.reclaim.classify_surfaces` already classifies
generated skill/agent wrapper files (and detects drift), but it has no
opinion on settings, hooks, rules, or lock files, because those are never
generated at all. This registry is what lets `explain-path` say "authored"
for those instead of nothing.
"""

from __future__ import annotations

import dataclasses


@dataclasses.dataclass(frozen=True)
class DirectoryOwner:
    prefix: str
    description: str


# Longest-prefix-first is resolved by `directory_owner` itself (by prefix
# length), not by declaration order here.
HYDRA_DIRECTORY_OWNERS = (
    DirectoryOwner("core", "Stable framework rules, principles, lifecycle, and placement policy."),
    DirectoryOwner("repo/knowledge", "Canonical repository-specific facts, conventions, and flat knowledge."),
    DirectoryOwner("repo/telemetry", "Bounded, author-attributed telemetry evidence packages."),
    DirectoryOwner("repo/postmortems", "Backward-looking incident records, one file per incident."),
    DirectoryOwner("repo", "Canonical repository-specific facts, conventions, and procedures."),
    DirectoryOwner("tasks/personal", "One owner's structured in-flight work and its checkpoints; tracked, owner-scoped."),
    DirectoryOwner("tasks/templates", "Task record and checkpoint templates."),
    DirectoryOwner("tasks", "Task-record definition and personal in-flight state."),
    DirectoryOwner("capabilities/agents", "Specialist roles and decision boundaries."),
    DirectoryOwner("capabilities/skills", "Reusable procedures and expertise."),
    DirectoryOwner("capabilities/workflows", "Repeatable coordination patterns."),
    DirectoryOwner("capabilities/tools", "Capability definitions, tool requirements, and integration requirements."),
    DirectoryOwner("capabilities", "Agents, skills, workflows, and tool capability records."),
    DirectoryOwner("adapters", "Provider, lifecycle, and runtime adaptation contracts."),
    DirectoryOwner("surfaces", "Contracts for human-facing and interface-specific documentation surfaces."),
    DirectoryOwner("cognition", "Derived or rebuildable retrieval structures."),
    DirectoryOwner("evolution/candidates", "Governed evolution candidates queue."),
    DirectoryOwner("evolution/reflections", "Dated, author-attributed session-observation packets."),
    DirectoryOwner("evolution", "Improvement evidence, experiments, and seed-candidate changes."),
    DirectoryOwner("validation", "Checks that keep the framework coherent."),
    DirectoryOwner("scripts", "Executable helper behavior; hydra.py is a compatibility entrypoint, not the implementation home."),
    DirectoryOwner("intake/migrations", "One shared workspace per migration effort: scope and a single ledger, never originals."),
    DirectoryOwner("intake/integrations", "Source integration workspaces: README, ledger, object map, collisions."),
    DirectoryOwner("intake/promoted", "Promotion records linking source material to the canonical files it changed."),
    DirectoryOwner("engine", "Hydra engine implementation (src/) and its tests (tests/)."),
)


@dataclasses.dataclass(frozen=True)
class ProviderRootDeclaration:
    prefix: str
    status: str  # "generated" or "authored"
    detail: str


PROVIDER_ROOT_DECLARATIONS = (
    ProviderRootDeclaration(".claude/skills", "generated", "Generated from capabilities/skills by export-adapters."),
    ProviderRootDeclaration(".claude/agents", "generated", "Generated from capabilities/agents by export-adapters."),
    ProviderRootDeclaration(".claude/settings.json", "authored", "Hand-maintained Claude Code settings."),
    ProviderRootDeclaration(".claude/settings.local.json", "authored", "Hand-maintained, per-clone Claude Code settings."),
    ProviderRootDeclaration(".claude/rules", "authored", "Hand-maintained path-specific Claude Code rules."),
    ProviderRootDeclaration(".claude/scheduled_tasks.lock", "authored", "Hand-maintained Claude Code scheduled-task lock state."),
    ProviderRootDeclaration(".agents/skills", "generated", "Generated from capabilities/skills by export-adapters."),
    ProviderRootDeclaration(".codex/agents", "generated", "Generated from capabilities/agents by export-adapters."),
    ProviderRootDeclaration(".codex/hooks.json", "authored", "Hand-maintained Codex hook configuration."),
)


def _longest_match(rel: str, prefixes: tuple):
    best = None
    for entry in prefixes:
        if rel == entry.prefix or rel.startswith(f"{entry.prefix}/"):
            if best is None or len(entry.prefix) > len(best.prefix):
                best = entry
    return best


def directory_owner(rel_to_hydra: str) -> str | None:
    """The `.hydra-framework/`-relative path's owning-directory description,
    or `None` if no registered directory claims it."""
    match = _longest_match(rel_to_hydra, HYDRA_DIRECTORY_OWNERS)
    return match.description if match else None


def provider_root_declaration(rel_to_root: str) -> ProviderRootDeclaration | None:
    """The repo-root-relative path's authored-versus-generated declaration,
    or `None` if it is not one of the provider-root paths this registry
    declares outright (most provider surfaces are classified instead by
    `providers.reclaim.classify_surfaces`, which this registry does not
    duplicate)."""
    return _longest_match(rel_to_root, PROVIDER_ROOT_DECLARATIONS)
