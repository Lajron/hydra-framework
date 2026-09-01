# Documentation Authoring

For canonical ownership and maintainer evidence, see the [Source Map](/project-wiki/hydra-framework/reference/source-map.md#maintainer-evidence).

Status: reference

The wiki is a human-facing explanation and navigation layer over canonical
Hydra state. Durable rules, reusable procedures, task records, validation
behavior, provider policy, and evolution records remain owned by
`.hydra-framework/`. Wiki prose routes to those owners through the Source Map
instead of copying their live state.

## Author and Review Contract

Before writing, read the canonical source for the subject. If the wiki and a
canonical source disagree, correct the canonical source first or record the
gap. Keep each page bounded to one reader job, state durable claims directly,
and place an inline wiki link or a nearby Source Map route beside claims that
need verification. Never cite `.hydra-framework.local/` from a
shared page.

Do not narrate the drafting process in the page. Commands, dates of checks,
search results, and source notes belong in the task record. A verified gap is
appropriate only when a reader needs to know that a claim is unsupported or
conflicts with its owner. Use `Do not duplicate` when the reader should follow
the canonical source instead.

The [Source Map](/project-wiki/hydra-framework/reference/source-map.md#maintainer-evidence)
routes to the audience, citation, synchronization, and authoring owners. This
page is the concise reference for human authors and reviewers, not a
replacement for those contracts.

## Page Types

| Page type | Use it for |
| --- | --- |
| Orientation | A short first explanation with a clear route onward. |
| FAQ | Questions readers actually ask, with brief answers and one route to the full explanation. |
| Operating guide | A repeatable workflow with commands and expected evidence. |
| Concept explainer | A mental model such as state tiers or provider surfaces. |
| Source map | Navigation from claims to canonical owners. |
| Review or onboarding summary | Reusable summaries whose evidence remains in cited sources. |
| Gap index | A checked mismatch or unresolved question with an owner and next action. |

## Visual Grammar

Use visuals to explain relationships, not as evidence. Prefer Mermaid for
editable flows, lifecycles, dependencies, and state relationships. Use a
vertical `flowchart TB` or `TD` by default, and use `LR` only for a genuinely
short sequence or a naturally wide timeline. Use a live, curated directory tree
for file layout. Mark omitted siblings when the tree is a subset, and use
box-drawing characters for branches. Use tables for precise ownership,
comparison, and status information.

Generated images and screenshots may support review or onboarding material, but repository facts
must remain in nearby text with canonical links. Pair icons with text labels.
Colors are optional aids, never the only state signal: green means confirmed,
amber pending or partial, red blocked or failed, blue process or navigation,
purple provider or generated, and gray external or derived.

## Validation

Run `python3 .hydra-framework/scripts/hydra.py validate-wiki` after adding,
moving, renaming, or deleting pages. It checks Markdown and Obsidian-style
links. Keep path citations accurate separately because backtick paths are not
validated by that command. When canonical Hydra files change, run the full
`python3 .hydra-framework/scripts/hydra.py validate` gate as well.

## Routes

Use [Reference](/project-wiki/hydra-framework/reference/reference.md) for the glossary and source map. Use
[Operations](/project-wiki/hydra-framework/operations/operations.md) for validation and troubleshooting.
