# First Task Walkthrough

For canonical ownership and maintainer evidence, see the [Source Map](/project-wiki/hydra-framework/reference/source-map.md#maintainer-evidence).

This example shows a small, visible wiki correction from first request to
completion. The same shape applies to code or framework work, but the
validation command changes with the surface.

## Scenario

A teammate asks to fix a stale link in a wiki page and to leave the work easy
to review. The change is small, but it is useful to make it visible when it
will span a handoff, a review cycle, or enough investigation that losing the
context would waste effort.

## 1. Orient and choose the state level

Read the repository entry guidance, then inspect active work:

```bash
python3 .hydra-framework/scripts/hydra.py board
python3 .hydra-framework/scripts/hydra.py knowledge-search "wiki links and validation"
```

If an active task already covers the correction, continue it rather than
creating another record. If the work is truly one-shot, inspect and correct the
page without creating task state. For this example, it needs review and may
pause, so start one owner-scoped task:

```bash
python3 .hydra-framework/scripts/hydra.py task start fix-wiki-link \
  --goal "Correct the stale wiki link and verify the wiki surface."
```

Fill in the record's readiness, step state, changed files, validation evidence,
and continuation notes immediately. The command creates the record but cannot
know those facts for you.

## 2. Read the owner and make the narrow change

Locate the target page and its owner before editing. For a wiki claim, read the
canonical source it links to; update that source first if the claimed behavior
is wrong. Change the stale link, preserve unrelated worktree edits, and record
the changed path in the task record.

Use scoped context when the request needs more than a direct page-and-source
read:

```bash
python3 .hydra-framework/scripts/hydra.py compile-context \
  --task "Correct a stale link in the Hydra wiki"
```

Context selection helps an agent find relevant canonical material. It does not
approve the edit or decide which repository state should persist.

## 3. Verify and preserve evidence

For this wiki-only example, run:

```bash
python3 .hydra-framework/scripts/hydra.py validate-wiki --path project-wiki
git diff --check
```

Record the commands and results in the task record. If the edit changes a file
under `.hydra-framework/`, also run the full framework validation gate:

```bash
python3 .hydra-framework/scripts/hydra.py validate
```

Treat a failure as evidence to investigate, not as a reason to retry the same
command without a new hypothesis. The task's next step should name the
remaining check or blocker.

## 4. Pause, hand off, or finish

When work pauses or someone else takes responsibility, checkpoint it and hand
it off rather than copying a conversation into the repository:

```bash
python3 .hydra-framework/scripts/hydra.py task checkpoint <name-or-path>
python3 .hydra-framework/scripts/hydra.py task handoff <name-or-path> --to <owner>
```

When review is complete, the corrected wiki page is the durable outcome. Name
it when completing the task:

```bash
python3 .hydra-framework/scripts/hydra.py task complete <name-or-path> \
  --outcome project-wiki/hydra-framework/working-with-hydra/first-task.md
```

Completion removes the active task record and its checkpoints because Git is
their archive. Review the printed Git status before committing: a task is not
fully landed while its outcome or task-state deletion remains uncommitted.

Continue with [Task Lifecycle](/project-wiki/hydra-framework/working-with-hydra/task-lifecycle.md) for the concise lifecycle
reference or [Execution Flow](/project-wiki/hydra-framework/architecture/execution-flow.md) for the system
trace behind this walkthrough.
