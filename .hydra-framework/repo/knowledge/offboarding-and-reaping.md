---
title: Offboarding And Reaping
status: active
created: 2026-08-25
owners:
  team: hydra
certainty: reviewed
provenance:
  sources:
    - .hydra-framework/engine/src/hydra_engine/work/task_records.py
    - .hydra-framework/engine/src/hydra_engine/commands/work.py
    - .hydra-framework/core/placement-rules.md
    - .hydra-framework/capabilities/workflows/task-lifecycle.md
---

# Offboarding And Reaping

## Purpose

What happens to a person's Hydra state when they leave the team, stop
responding, or their task record simply goes stale -- and how to tell a
merely-quiet task apart from one that actually needs to be taken over.

Hydra keeps no roster of who is currently a valid owner, so "is this owner
still active" is always answered outside Hydra -- ask the team or check the
host's real membership system, never a Hydra-file lookup.

## The Signal: Staleness, Not Absence

`hydra.py board` and `hydra.py validate`'s personal-task advisory notes flag
a record whose `Updated:` date is older than `STALE_TASK_DAYS` (14). This is
the only mechanical signal Hydra gives that a task record might be
orphaned. It is a prompt to check, not a verdict:

- The owner might be back from leave next week.
- The work might be genuinely paused, correctly, with `Status: blocked` and a
  real blocker recorded.
- The owner might have left the team, in which case the record is a real
  offboarding candidate.

A stale record is never reaped automatically, and never edited or deleted by
someone other than its owner without going through the mechanisms below --
that is exactly the ownership-safety invariant task ownership safety work
built: `checkpoint`, `handoff`, and `complete` all refuse to write another
owner's record without an explicit `--force` override.

## Taking Over An Offboarded Owner's Work

1. Confirm, outside Hydra, that the owner is actually gone (or genuinely
   unreachable for the duration this work needs) -- a real conversation, not
   a guess from a stale date alone.
2. If the work should continue, the new owner runs `hydra.py task handoff
   --force` naming the record. Handoff refuses to clobber the destination
   owner's own unrelated in-flight record even with `--force` -- it will not
   silently merge two people's work into one file.
3. If the work should not continue -- abandoned, superseded, or no longer
   relevant -- whoever is resolved as the record's owner (the departing
   owner, or the new owner after handoff) runs `hydra.py task complete
   --outcome <path|none>`. The record is deleted; Git history is the
   archive, per placement-rules' Personal tier rule.

Never delete or hand-edit another owner's task record file directly. The
commands above exist so a takeover is deliberate and attributed, not a
silent directory edit that looks the same as the owner's own work.

## Duplicate Work Is A Related, Different Problem

`hydra.py validate`'s `duplicate-task-work` check flags two different owners
holding an active record with the same task slug. That is not an offboarding
signal by itself -- it usually means two people started the same work
without knowing about each other, not that either one left. Resolve it by
talking to both owners, then use `handoff` (one person takes over the other's
record) or `complete` (one record was redundant and its work folds into the
other), the same mechanisms this file already describes -- never by silently
deleting either owner's file.
