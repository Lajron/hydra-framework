---
title: Knowledge Packages
status: active
owners:
  team: hydra
certainty: confirmed
provenance:
  sources:
    - .hydra-framework/repo/knowledge/knowledge-packages/templates/overview.md
---

# Knowledge Packages

A knowledge package is a repeated local structure for a repository area that has enough durable complexity to deserve its own mini knowledge base.

Hydra should use knowledge packages for apps, services, libraries, bounded contexts, domains, automation areas, integration areas, or other meaningful repository regions.

## Purpose

Knowledge packages let Hydra support breadth and depth at the same time:

- breadth: many packages can share a predictable shape
- depth: each package can contain specialized facts, risks, questions, sources, and procedures

This repetition is useful when it improves retrieval, handoff, validation, and agent behavior. It is not a reason to duplicate canonical facts.

## Recommended Shape

```text
knowledge-packages/<package-slug>/
  routing.yaml          # package selection + routes -- the one machine entrypoint
  state.md              # <= 40 lines, pointer only
  overview.md           # optional: boundaries and source-of-truth policy
  sources.md            # authority anchors, cited by unit provenance
  problems.md           # unresolved issues that are not divergences
  definition-of-done.md # explicit stop condition
  units/
    <slug>.md           # one durable operational question per file, flat --
                         # `group:` in frontmatter is metadata only, not a directory
```

Use only the files a package actually needs. Templates live under
`knowledge-packages/templates/`; they are defaults for new packages, not a
mandatory file count. A package with just `routing.yaml` and one unit is
already a legal package -- and below roughly five durable questions, a
single `overview.md` is correct; do not manufacture units to reach a target
count.

## Ownership

- `routing.yaml`: package selection (`keywords`) and `routes:` -- the machine
  entrypoint. A route names the `units/` its task shape needs
  (`priority_units`), which ones are budget-exempt (`requires`), and what to
  avoid reading by default. See the worked example in
  `knowledge-packages/templates/routing.yaml`.
- `state.md`: short active pointer and latest handoff, not a log.
- `overview.md`: durable summary, boundaries, source-of-truth policy, and
  reading map.
- `sources.md`: authoritative external references and intake provenance,
  cited by unit `provenance.sources`.
- `problems.md`: concrete unresolved issues with evidence and next action
  that are *not* a divergence between authority and implementation --
  those become a `unit_kind: divergence` unit instead. `problems.md` is not
  a wishlist.
- `definition-of-done.md`: explicit stop condition so packages do not grow by
  polish alone.
- `units/<slug>.md`: one durable operational question per file, addressable
  by `hydra://knowledge-unit/<package>/<slug>` and compiled by
  `compile-context` via its `reads:`. See
  `capabilities/skills/knowledge-unit/skill.md` for how to write one.

## Status Discipline

Use `repo/knowledge/certainty-model.md`'s states (`confirmed`, `inferred`,
`assumed`, `unresolved`, `conflicting`, `superseded`, `rejected`) in a unit's
`certainty:` field, or a route/package's own prose, rather than a separate
package-local vocabulary. The one rule worth stating on its own: do not
present design-stage material as shipped behavior -- write it as
`certainty: unresolved` or `status: planned`, not as a prose marker.

## Routing And Hooks

Provider adapters use package `routing.yaml` files to emit small prompt-time
pointers such as "read package state and overview first," plus, when a route
matches, that route's `priority_units`/`requires` as a menu of unit
questions. The hook output should remain a pointer, not a content dump.

Package-local post-edit hooks should run deterministic gates only: link
checks, path checks, unit validation (`validate_units_dir`), diagram
rendering when requested, generated-surface freshness, or other cheap
validation owned by the package. Broad reasoning belongs in tasks or
reviews, not hooks.

## Validation Defaults

The default package gate checks internal Markdown links, the package's
`routing.yaml`, its `units/` directory, and optionally renders DOT diagrams
when `--render` is passed. Repositories may add stricter package-local
checks when the package owns generated artifacts or cited source paths.

## Rules

- Do not create a knowledge package for every folder.
- Create one when local durable knowledge is repeatedly useful.
- Keep shared concepts in global `repo/knowledge/`.
- Keep package-specific specialization in the package.
- Link to Git, CI, issue trackers, and docs platforms instead of mirroring their state.
- Archive or supersede package notes when they stop being authoritative.
- Write a unit only when a route or another unit's `requires`/`see_also`
  will point at it. A unit nothing points at is wiki material, not a unit.
