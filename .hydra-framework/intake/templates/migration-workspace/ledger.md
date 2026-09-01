
# Migration Ledger: <short-name>

Type: migration-ledger
Status: active
Created: YYYY-MM-DD

One row per source item. This is the only inventory; do not keep a second
placement map beside it.

## Status Values

- `pending`: not yet triaged.
- `promoted`: durable meaning is under a canonical owner and the original is drained.
- `kept-private`: stays in private staging only. Nothing shareable in it.
- `rejected`: no durable meaning. Recorded so nobody re-triages it.
- `redirected`: original left in place as a stub pointing at the new authority.
- `deferred`: real value, out of this migration's scope. Needs a follow-up owner.

Terminal statuses are everything except `pending` and `deferred`. A `deferred`
row must name its follow-up before the migration can close.

## Ledger

| Source | Verdict | Destination | Status | Notes |
| --- | --- | --- | --- | --- |
| `docs/example.md` | promote | `project-wiki/<project>/example.md` | pending | |
| `docs/private/*` (N files) | private | — | kept-private | grouped; filenames not recorded |

## Counts

- Total items:
- Terminal:
- Pending:
- Deferred:

Update counts at each checkpoint. A migration that cannot state these numbers
does not know whether it is finished.

## Grouped Rows

A row may cover a set when the items share one verdict and one destination.
Record the count. Group rather than enumerate when the filenames are themselves
sensitive.
