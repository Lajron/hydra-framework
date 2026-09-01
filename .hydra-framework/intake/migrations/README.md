---
hydra_id: hydra://migration-ledger/intake-migrations
uid: 3c1cf7d8-e449-418d-b928-9e99f59fc9c5
schema_version: 3
kind: migration-ledger
title: Intake Migrations
status: active
scope: base-seed
owners:
  team: hydra
relations: []
provenance:
  sources:
    - .hydra-framework/capabilities/workflows/material-migration.md
---

# Intake Migrations

A migration workspace groups one bounded effort to clear a source area — a
transferred docs folder, an inherited wiki, a per-developer notes pile — into
its correct canonical owners.

Use one workspace per effort:

`intake/migrations/<YYYY-MM-DD>-<slug>/`

Start from `intake/templates/migration-workspace/`.

## Why This Exists

Ordinary intake is per-item: one source, one triage note, one promotion record.
That is correct for a single article or report, and wrong for four hundred files
that need a shared verdict, a shared destination map, and an answer to "is this
finished."

A migration workspace adds only what per-item intake lacks: a grouping container,
one ledger covering every item, and an explicit end state.

## Contents

- `README.md`: source roots, where originals were moved, scope, definition of done.
- `ledger.md`: one row per source item with verdict, destination, and status.
- `batches/<batch>/state.json`: machine-readable gates, bounded actions,
  proposal/validation digests, human outcomes, and reconciliation history.
- `batches/<batch>/drafts/`: bounded package/unit proposal files awaiting
  independent validation and publication approval.

Anything needing full provenance, a privacy review, or a substantial promotion
still uses `raw/`, `triage/`, and `promoted/`. The ledger row links to it. Small
obvious items need only their ledger row.

## Originals Stage By History

Before promoting anything, an agent inventories the source area and requests a
bounded staging move. A human approves the exact source roots, route, destination,
and reversible action; approval performs the move automatically:

- Already-shared or safe-to-track material stages under tracked
  `.migrations/<source-slug>/`.
- Private, sensitive, ignored, or never-committed material stages under
  `.hydra-framework.local/migrations/<slug>/originals/`.

That single move drains the repository, is reversible, and needs no separate
snapshot.

The workspace here is shared and Git-tracked. Private originals are not.
Teammates can read what a migration decided without gaining access to material
that was never theirs to read. For already-shared material, the staged source
remains shared and citeable from the ledger while it is being drained; staging
does not make it canonical Hydra knowledge.

This split is what makes the same mechanism work for both repository shapes: a
repository where the docs were already committed and shared, and a repository
where each developer keeps a private pile they may want partially shared.

## Rules

- Move originals only through an approved staging request and before promoting
  anything. Never delete a source file as the first action.
- Require one bounded human decision (`approve`, `reject`, or `revise`) before
  staging, canonical publication, and final staged-original removal. New package
  boundaries, conflicts, sensitive/private findings, and ambiguity join the
  same coherent batch request.
- Require fresh validation from an independent agent instance with no drafting-
  chain context before every canonical publication request. Record provider-
  neutral capability classes, not provider/model names.
- Do not put the originals in this directory. It is Git-tracked.
- Do not record a private path, filename, or heading in the ledger when the
  filename itself is the sensitive part. Group those rows and describe the set.
- A migration is done when every ledger row has a terminal status, not when the
  useful material has been promoted.
- Approved closure removes only the exact reconciled staged originals and keeps
  the workspace. It records what was published, redirected, rejected, or kept
  private, which is the part nobody can reconstruct later.

## Canonical Sources

- `.hydra-framework/capabilities/workflows/material-migration.md`
- `.hydra-framework/repo/knowledge/intake-lifecycle.md`
- `.hydra-framework/core/placement-rules.md`
