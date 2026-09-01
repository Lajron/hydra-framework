---
title: Propagating A Structural Change To Downstream Copies
status: active
created: 2026-07-30
owners:
  team: hydra
certainty: confirmed
provenance:
  sources:
    - .hydra-framework/core/placement-rules.md
    - .hydra-framework/repo/knowledge/silent-failure-modes.md
    - .hydra-framework/scripts/hydra.py
---

# Propagating A Structural Change To Downstream Copies

## Purpose

How a change that moves or deletes files reaches a repository that already
copied Hydra.

Written when most state moved to its current tiers, but the procedure
generalizes: any change that alters *where* state lives has the same problem, and
a file copy is the wrong tool for all of them.

## Why This Is Not A File Copy

Three reasons, each of which has already caused a real failure or would have.

**A recursive copy destroys the lineage block.** `manifest.yaml` in an adopting
repository carries `lineage:`; the seed has none. Copying the seed's manifest
down deletes it silently, and the next `diff-base` cannot separate deliberate
divergence from drift. See `silent-failure-modes.md` entry 5. **Never copy
`manifest.yaml` downstream.**

**The downstream repository has its own records.** A structural change to task
state has to act on *that* repository's files, which the seed has never seen.
Copying the seed's tree would either miss them or overwrite them.

**Deletions do not travel by copying.** Copying adds and overwrites. The retired
directories would survive downstream, still holding records, and nothing about
the copy would say they should not.

The seed ships the *mechanism* — `hydra.py migrate-state` — and the downstream
repository runs it against its own state. That is why the migration is a command
and not a paragraph in a document: a documented-but-manual migration is one that
gets done differently in each repository.

## Procedure

Run in the downstream repository.

1. **Record the starting point.**

   ```bash
   python3 .hydra-framework/scripts/hydra.py diff-base --base <path-to-seed> --json > /tmp/before.json
   ```

   Keep it. It is how you tell a difference this change introduced from one that
   was already there.

2. **Take the shared changes**, by whatever mechanism the copies use — merge,
   cherry-pick, or targeted file updates. Update `core/`, `repo/knowledge/`,
   `capabilities/`, `scripts/`, `tasks/templates/`,
   `AGENTS.md`, and `AI_SYSTEM.md`.

   Do not touch `manifest.yaml` beyond hand-merging the new `state_tiers:` block
   and private-tier shape pointer into it. Its `lineage:` block must survive.
   If the change removes a formerly copied tree, delete that tree explicitly in
   the downstream copy; deletions do not travel by copying.

3. **Preview the migration.**

   ```bash
   python3 .hydra-framework/scripts/hydra.py migrate-state
   ```

   It reports moves, deletions, retirements, and README drops without changing
   anything. Read it. In particular, check which records it plans to delete
   versus retire: deletion means Git already holds the file, retirement means it
   does not and the working copy is the only copy.

4. **Apply it.**

   ```bash
   python3 .hydra-framework/scripts/hydra.py migrate-state --apply
   ```

   Records land under `tasks/personal/<owner>/`, attributed from each record's
   `Owner:` header. Records with no owner fall to whoever runs the migration,
   which is correct when each engineer migrates their own copy and wrong if one
   person migrates a shared checkout — in that case, fix the `Owner:` headers
   first.

5. **Regenerate and verify.**

   ```bash
   python3 .hydra-framework/scripts/hydra.py export-adapters
   python3 .hydra-framework/scripts/hydra.py doctor
   python3 .hydra-framework/scripts/hydra.py selftest
   ```

6. **Confirm private state is actually private.**

   ```bash
   git status --porcelain .hydra-framework.local
   ```

   Empty output is the pass. `.hydra-framework.local/` is matched by a
   directory-level ignore that covers paths which do not exist yet, so this
   should hold without adding patterns.

7. **Compare against the seed again.**

   ```bash
   python3 .hydra-framework/scripts/hydra.py diff-base --base <path-to-seed>
   ```

   Expect only the lineage stamp and whatever `/tmp/before.json` already showed.
   Anything new is either an incomplete step above or a genuine local adaptation
   — record the latter with `evolution record` rather than leaving it
   unexplained.

## What The Comparison Will And Will Not Show

`diff-base` compares framework *definition*, so:

- `tasks/personal/` is excluded. Moving records in or out is invisible to it,
  which is why step 6 checks Git directly instead.
- `tasks/templates/` **is** compared. It previously fell under a blanket
  `tasks/` exclusion, so template drift between a seed and a copy was
  invisible. A first comparison after that change may surface template
  differences that were always there and simply could not be seen.
- `intake/raw|extracted|triage/` and `repo/pending/` leave `.hydra-framework/`
  entirely, so they drop out of scope structurally rather than by exclusion list.
  If they still appear, step 4 did not run.

## Order Matters

Take the shared changes before running `migrate-state`. The migration is
implemented in the new `hydra.py`; running the old one does nothing, and running
the new one against an un-updated tree leaves docs describing directories that no
longer exist.

## Related

- `core/placement-rules.md`
- `repo/knowledge/seed-reconciliation.md`
- `repo/knowledge/silent-failure-modes.md`
- `repo/knowledge/state-tiers.md`
