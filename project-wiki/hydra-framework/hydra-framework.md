# Hydra Framework

Hydra is repository-contained, provider-neutral AI-work infrastructure. It
gives people and AI agents a shared, inspectable working layer for canonical
knowledge, reusable capabilities, owner-scoped task state, provider adapters,
and mechanical validation.

Start with the root [README](/README.md) for the public explanation and
quick start. This page is the wiki route map: it sends each reader to operating
guides and source-traceable detail without repeating the landing page.

`.hydra-framework/` is the canonical shared system. `.hydra-framework.local/`
is private machine and developer state. `project-wiki/` explains and routes
the system for humans. The [Source Map](/project-wiki/hydra-framework/reference/source-map.md#maintainer-evidence)
holds the governing boundaries and maintainer evidence.

## Current Status And Boundaries

Use the [Source Map](/project-wiki/hydra-framework/reference/source-map.md#maintainer-evidence)
to reach the canonical records for changing status and deliberate limits:

- Build status
  is the capability-by-capability implementation inventory.
- Known problems
  records open concerns and their evidence.
- Package state
  carries the current handoff and explicitly deferred behavior.
- Unresolved questions
  lists high-impact questions that remain intentionally open.

## Choose A Route

| Reader | Start here | Route |
| --- | --- | --- |
| Evaluator | [Root README](/README.md) | Promise, verified benefits, quick start, and claim boundaries |
| New contributor | [Post-clone path](/project-wiki/hydra-framework/start-here/new-contributor.md) | Setup, orientation, first change, validation |
| Daily Hydra user | [Working With Hydra](/project-wiki/hydra-framework/working-with-hydra/working-with-hydra.md) | Context, task state, execution, validation |
| Architecture engineer | [Concepts](/project-wiki/hydra-framework/concepts/concepts.md) | State tiers, execution stack, runtime flow |
| Hydra maintainer | [Extending Hydra](/project-wiki/hydra-framework/extending-hydra/extending-hydra.md) | Capabilities, adapters, knowledge, migration |
| Operator | [Validation](/project-wiki/hydra-framework/operations/validation.md) | Health checks, validation, operational commands |
| Reviewer tracing claims | [Source Map](/project-wiki/hydra-framework/reference/source-map.md) | Wiki claim, canonical owner, code or evidence |
| Public-doc maintainer | [Positioning Brief](/project-wiki/hydra-framework/reference/public-positioning.md) | Audience, terminology, claims to defer, evidence backlog |

## First Stops

- [Start here](/project-wiki/hydra-framework/start-here/start-here.md) orients a new reader and links all
  audience routes.
- [Common questions](/project-wiki/hydra-framework/start-here/common-questions.md) answers focused questions
  and points to the page that owns each detailed explanation.
- [Working With Hydra](/project-wiki/hydra-framework/working-with-hydra/working-with-hydra.md)
  and [New Contributor](/project-wiki/hydra-framework/start-here/new-contributor.md)
  define the repository and agent starting routes.
- [Public Positioning Brief](/project-wiki/hydra-framework/reference/public-positioning.md) owns public
  terminology and evidence discipline, not framework behavior.
