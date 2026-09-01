---
title: Intake Lifecycle
status: active
owners:
  team: hydra
certainty: confirmed
provenance:
  sources:
    - .hydra-framework/core/placement-rules.md
    - .hydra-framework/capabilities/workflows/material-migration.md
---

# Intake Lifecycle

Hydra uses intake to prevent unverified material from becoming permanent memory too early.

The lifecycle is:

`source -> raw -> extracted -> triage -> promoted -> canonical-or-archived`

## Stages

Processing is private; only the outcome is shared. The placement rules set this
boundary.

| Stage | Where | Tracked |
| --- | --- | --- |
| `source` | external system, file, tool output, or observed behavior | n/a |
| `raw` | `.hydra-framework.local/intake/raw/` | no |
| `extracted` | `.hydra-framework.local/intake/extracted/` | no |
| `triage` | `.hydra-framework.local/intake/triage/` | no |
| `promoted` | `.hydra-framework/intake/promoted/` | yes |
| `canonical-or-archived` | the canonical owner | yes |

- `raw`: source descriptor or safe source copy awaiting processing.
- `extracted`: generated, source-derived artifact such as text, links, parsed metadata, OCR, or structured output.
- `triage`: reviewed staging note that separates useful facts, uncertain claims, conflicts, privacy concerns, and promotion targets. Triage is a judgment in progress, which is exactly the kind of thing people only write honestly when it is not permanent.
- `promoted`: traceability record showing what moved into canonical state.
- `canonical-or-archived`: verified durable knowledge is stored under its owner; stale or untrusted material is archived or superseded.

## Canonical Boundary

Intake material is not trusted memory.

The boundary is now structural rather than a rule to remember: the early stages
are in the untracked private tier, so nothing there can be authoritative for the
team. Hydra can use it during an active investigation, but durable knowledge
belongs only in the appropriate canonical owner:

- `repo/knowledge/`
- `capabilities/`
- `evolution/`

## The Promotion Record Must Stand Alone

A promotion record is shared; the source descriptor it came from is private.

**Do not link a promotion record to `.hydra-framework.local/`.** Whoever wrote it
can follow that path; no teammate can, and a reader cannot distinguish a real
citation from one they simply lack.

Copy the durable content of the descriptor into the promotion record: origin URL
or system, date checked, licence or privacy note, and the claim being promoted.
The private descriptor stays disposable. `hydra.py validate` fails when a shared
file cites a private file.

## Promotion Criteria

Promote material only when it is:

- useful beyond the current prompt
- safe to share in Git
- verified or clearly marked by certainty level
- placed under a clear owner
- not already represented by an authoritative external system
- reduced to durable meaning rather than copied raw history
- self-contained, carrying what it needs rather than pointing at private material

## Notes Versus Intake

Use `.hydra-framework.local/notes/` for lightweight unverified observations:
`hydra.py note "<title>"` creates a dated titled note, while stdin-only input
appends to today's scratch note.

Use `intake/` when there is a larger source-processing workflow, generated extraction artifact, privacy review, provenance chain, or promotion decision.

There is no shared `repo/pending/`: it answered no question about the
repository, no item said who put it there, and nothing forced items toward a
terminal end. The placement rules state the general test a shared queue must
pass instead.

## Reflection Versus Intake

Intake processes external source material; reflection processes observations
about using the framework itself. Intake's early stages are private because
source material is unreviewed. Reflection packets in `evolution/reflections/`
are shared from the start, because their whole purpose is review by someone
other than the author — see `evolution/reflections/README.md`.

## Item Intake Versus Migration

The stages above process one source at a time and end at `promoted`. They never
drain the source, because for an article, report, or tool output there is nothing
to drain.

Clearing a whole source area is different work. It needs a grouping container, a
single ledger covering every item, and a definition of done that includes the
source area being empty. Use `intake/migrations/<date>-<slug>/` and follow
`capabilities/workflows/material-migration.md`.

Two rules distinguish it from item intake:

- Agents inspect and inventory first, then a human approves the exact staging
  roots and reversible move before originals enter `.migrations/<slug>/` or
  `.hydra-framework.local/migrations/<slug>/originals/`. Approval applies the
  move automatically. Never delete a source file as the first action, and never
  assume Git holds a copy without checking — ignored and never-committed folders
  are common in exactly the material that most needs migrating.
- Completion is measured by the ledger, not by what was promoted. `rejected` and
  `kept-private` are terminal outcomes. A migration that only tracks successful
  promotions cannot tell a finished effort from an abandoned one.
- Canonical publication requires a fresh independent validator agent instance
  with no drafting-chain context, followed by a bounded human approval. Closure
  reconciles every item and requires a final approval for the exact staged paths
  to remove; the shared ledger/workspace remains the audit trail.
