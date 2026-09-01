# Concepts

Hydra is a repository-owned operating layer for AI-assisted engineering. It
makes the context, instructions, tools, state, feedback, and handoffs around a
model explicit so work can continue across sessions and providers instead of
depending on raw chat history. The runtime model and its responsibilities are
explained in [Architecture](/project-wiki/hydra-framework/architecture/architecture.md).

For canonical ownership and maintainer evidence, see the [Source Map](/project-wiki/hydra-framework/reference/source-map.md#maintainer-evidence).

Hydra exists to make AI-assisted work recoverable and team-owned. The repository
holds canonical rules and knowledge, personal task state preserves resumable
work, and private state keeps personal thinking and machine details out of
shared documentation. The placement boundary is explained in the [State Tiers](/project-wiki/hydra-framework/concepts/state-tiers.md)
guide.

Use this area for the two foundations of the framework:

- [State tiers](/project-wiki/hydra-framework/concepts/state-tiers.md) explains where shared, personal, and private
  state belongs.
- [Architecture](/project-wiki/hydra-framework/architecture/architecture.md) routes to the runtime stack
  and the end-to-end execution flow.
