---
title: Runbook - Interrupted Hydra Write
status: active
created: 2026-08-27
owners:
  team: hydra
certainty: confirmed
provenance:
  sources:
    - .hydra-framework/engine/src/hydra_engine/objects/references.py
    - .hydra-framework/engine/src/hydra_engine/work/task_records.py
---

# Runbook: Interrupted Hydra Write

What to actually do when a Hydra write was interrupted, a registry merge
conflicted, or a task handoff crashed partway through. Every write here is
atomic (temp file plus `os.replace`) and every derived structure rebuilds
from canonical files on disagreement, which is why these are safe to leave
and self-heal, rather than needing a lock.

## A crashed write left a stray temp file

Every Hydra write goes to `.<name>.hydra-tmp-<pid>` in the same directory,
then an atomic `os.replace` into place. A process dying between those two
steps (killed, out of memory, machine power loss) can leave the temp file
behind; the real file is always either the old content or the new content,
never truncated.

**Do:** delete any `.hydra-tmp-` file you find. It is always safe — it was
never the file anything reads. `.gitignore` already excludes the pattern, so
it never reaches a commit.

**Do not:** try to inspect it for recovery. If the write it represents still
needs to happen, rerun the command that produced it.

## The object registry has a merge conflict, or looks stale after a merge

`.hydra-framework/cognition/graph/registry.yaml` is fully derived from
canonical object metadata. `.hydra-framework/hooks/post-merge` already reruns
`hydra.py ref index` best-effort after every merge, so this should be rare;
it fires when the hook was not installed, failed silently, or the merge
happened somewhere the hook doesn't run (a squash merge on a host, for
example).

**Do:** take either side of the conflict — it does not matter which — and
run `hydra.py ref index`. Then `hydra.py ref check` to confirm.

**Do not:** hand-resolve the conflicting lines. Nothing about a manually
merged registry is trustworthy: digests from one branch can be stale against
the other branch's canonical files, and the resolver already treats
disagreement between a derived form and canonical metadata as a rebuild
trigger, never something to reconcile by hand.

If `ref check` still fails after reindexing, the problem is upstream of the
registry — a canonical object file itself has a conflict marker or a broken
reference. Fix that file; rerun `ref index`.

## A task handoff was interrupted partway through

`hydra.py task handoff` writes the destination task record before copying
checkpoints and deleting the source, so a crash mid-copy can leave
checkpoints split across the old and new owner.
`work/task_records.py`'s `duplicate_task_slug_findings` (code
`duplicate-task-work`) already reports this state.

**Do:** rerun the same `hydra.py task handoff` command. It completes a
half-done handoff rather than refusing on `destination already exists`,
because the destination is only refused when its content disagrees with what
this handoff would produce — a genuine name collision — not when it matches
what was already written before the crash.

**Do not:** manually delete or move checkpoint files to "fix" the split.
Rerunning the command is the tested recovery path; hand edits are not.

## A retry-state or telemetry counter looks wrong

`.hydra-framework.local/monitoring/retry-state.jsonl` and the knowledge
telemetry log are append-only JSONL: every event is a line, and the current
count is the aggregate of lines for a fingerprint since its last reset.

**Do:** if the file has grown large enough that `doctor` raises the growth
advisory, delete it. The counter simply restarts from zero; nothing else
depends on its history.

**Do not:** hand-edit lines to "correct" a count. Append a reset tombstone
(or just delete the file) instead of rewriting history in place.
