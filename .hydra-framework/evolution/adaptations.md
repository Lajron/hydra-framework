---
hydra_id: hydra://integration-ledger/base-seed-adaptations
uid: afdd5280-5d09-48cd-a6ae-dc6c0d80d6c3
schema_version: 3
kind: integration-ledger
title: Adaptations Ledger
status: active
scope: base-seed
owners:
  team: hydra
relations: []
provenance:
  sources:
    - .hydra-framework/scripts/hydra.py
---

# Adaptations Ledger

Status: active
Updated: 2026-07-30

Append-only record of intentional Hydra changes made after a repository adopts a
base seed. `hydra.py diff-base` reads it to separate deliberate divergence from
stale drift. Read it on demand during reconciliation; it is not always-on
context.

Prefer `hydra.py evolution record` over hand-editing: it writes the shape below
and refuses entries that would fail `hydra.py validate`.

Each entry is one `##` section. The field labels are matched literally:

- `## <YYYY-MM-DD> - <short title>`
- `Base seed version:` — the base version at the time of the change
- `Disposition:` — `repo-local` (correct here, not intended for the shared seed)
  or `promote-candidate` (may belong in the shared seed after reconciliation)
- `Paths touched:` — one `-` bullet per path, relative to `.hydra-framework/`
- `Why:` — one or more `-` bullets
- `Evidence:` — one or more `-` bullets

Record deletions as well as additions. A deliberate local deletion with no
ledger entry is indistinguishable from stale drift at the next comparison.

Whether this ledger should have entries depends on which repository you are in,
so check rather than assume: if `manifest.yaml` has no `lineage:` block, this
copy is the base seed, it has nothing to diverge from, and an empty ledger is
correct. If `lineage:` is present, this is an adopting repository and every
intentional change to `.hydra-framework/` belongs here.

Entries are appended below this line; do not add a `##` heading that is not an
entry.
