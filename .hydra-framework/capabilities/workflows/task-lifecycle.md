---
hydra_id: hydra://capability/workflow/task-lifecycle
uid: a91b62c7-b94a-4b8f-b8ba-8cb3bcbbd533
schema_version: 3
kind: workflow
title: Task Lifecycle Workflow
status: active
scope: base-seed
owners:
  team: hydra
relations:
provenance:
  sources:
    - .hydra-framework/core/placement-rules.md
    - .hydra-framework/repo/knowledge/state-tiers.md
---

# Task Lifecycle Workflow

This file is the canonical prose description of Hydra's task-record contract.
`REQUIRED_TASK_SECTIONS` in
`.hydra-framework/engine/src/hydra_engine/checks/task_contract_docs.py` is the
executable definition, and `tasks/templates/task.md` is the fill-in form.
`hydra.py validate` checks all three against each other, so a change to one must
land in all three.

Other documents should link here rather than restating the field list.

## Flow

understand -> resolve uncertainty -> check readiness -> plan -> approve -> execute step -> verify step -> learn

## Where Records Live

Records live in `.hydra-framework/tasks/personal/<owner>/`, one directory per
engineer, with checkpoints in `<owner>/checkpoints/`.

They are tracked in Git. That is deliberate: a record survives a lost machine,
follows its owner between machines, and can be read by whoever inherits the work.
Owner scoping is what keeps "active" meaning something: `tasks/personal/dana/`
is unambiguously Dana's in flight work, where a shared `tasks/active/` degrades
into whatever anyone left behind.

Your owner slug resolves from `--owner`, then `HYDRA_OWNER`, then
`git config user.email`, slugified as the full resolved candidate. If none is
set, commands fail rather than guessing; a default owner is how several people
end up writing into one directory.

Read anyone's record. Edit only your own.

Private thinking, planning, open questions, reactions, and scratch do not belong
in a record. It goes in `.hydra-framework.local/`, which is untracked.
`hydra.py note "<title>"` captures it as a dated titled private note with no
template.

## Persistence Triggers

Create task state when work is non-trivial, interrupted, blocked, multi-session,
handed off, or important for team visibility.

A task is non-trivial when losing the current conversation would make the next
agent waste meaningful tokens or risk doing the wrong thing.

Do not make every prompt a task.

## Required Fields

A persisted non-trivial task record must contain all of the following.

### Owner

The owner slug of whoever is responsible for the work right now. It matches the
directory the record sits in, and `task handoff` rewrites both together.

Attribution is not decoration here: it is how eight engineers avoid editing each
other's understanding of the same work.

### Updated

The date the record last changed, as `YYYY-MM-DD`.

`hydra.py board` displays it and `validate` notes records untouched for more than
fourteen days. Every command that modifies a record moves this field, and so must
a hand edit. A date that lies is worse than no date, because it reads as
confirmed-current.

This is distinct from `Created:`, which never changes.

### Goal

The engineering objective, in enough detail that another agent could resume
without the originating conversation.

### Readiness

Checked before execution. Small read-only tasks may mark readiness
`not-required`.

- **Status:** readiness state, such as `not-checked`, `ready`, `blocked`, or `not-required`.
- **Branch or workspace assumptions:** the branch, worktree, or working-tree state execution assumes.
- **Relevant canonical docs:** the Hydra or repository docs this work depends on, or `none identified`.
- **Required dependencies, services, generated artifacts, or private local requirements:** what must exist or run first, including anything that lives only in `.hydra-framework.local/`.
- **Blockers and assumptions:** anything that would make execution unreliable, stated explicitly rather than assumed silently.
- **Expected validation command or evidence:** how completion will be proven.

The required private local state field may name concrete `.hydra-framework.local/`
files when that path is necessary for another agent to resume the work on the
same machine. Those paths are still not shared evidence; any durable claim that
depends on private material must inline the verified claim instead of citing the
private source.

When `repo/knowledge/high-overhead-workflows.md` makes a workflow required,
record the trigger and selected control in Readiness or Step State before
execution. Required controls are part of the task's resumable state, not private
judgment.

### Step State

Maintained after meaningful progress.

- **Active step:** what is in flight now.
- **Next step:** what follows, so a handoff does not need to re-plan.
- **Completed steps:** what is done, plus superseded or skipped steps and what replaced them.

Also record the current stage, changed files, and validation evidence as work
proceeds.

### Continuation Notes

What another model or developer needs to continue safely. Facts,
never a conversation transcript.

- **Running state:** live state a resuming agent cannot rediscover from the repository: background processes with their shell or process IDs and how to stop them, dev servers and ports, and open worktrees or branches beyond the assumptions already recorded in Readiness. Write `none` rather than omitting the field.
- **Resume check:** the command a resuming agent should run first to confirm this record still matches reality, and the expected outcome. This is narrower than Readiness' expected validation command, which proves completion, and narrower than accumulated validation evidence, which records what has already been proven.

## Checkpoints

Create a checkpoint when work pauses, context is low, a blocker appears, a model
handoff is likely, or another developer needs to continue.

## Handoff

`hydra.py task handoff <record> --to <owner>` moves the record into the new
owner's directory and rewrites `Owner:`. Checkpoints follow it.

There is no separate shared handoff artifact, because the record is already
tracked and readable. The manual equivalent is `git mv` plus editing one line.
nothing about handoff requires an agent.

Moving a file is not telling someone. Tell them.

## Completion

`hydra.py task complete <record> --outcome <path|none>` **deletes** the record
and stages the task/checkpoint deletion when Git allows it.

There is no completion record and no archive copy. Git holds every version, and
duplicating state Git owns is what placement rules forbid. Recover a finished
record with `git log --diff-filter=D -- <path>`.

Deleting on completion is what keeps the tracked set to work genuinely in flight
rather than an ever-growing archive of eight people's finished scaffolding.
After completion, inspect the printed `git status` summary. If it lists
uncommitted changes, the task lifecycle is not fully landed until the outcome
changes and staged task-state deletion are committed.

`--outcome` is required. `none` is allowed when the work produced no durable
artifact. Otherwise it must name a repository-relative existing file. The command
refuses directories, paths outside the repository, task records/templates,
private local state, Git internals, and private intake staging areas.

This is a mechanical durability check, not a semantic review of the file's
contents. It forces the promotion question at the one moment it is cheap to
answer: where did the durable meaning go? Preserve only durable outcomes:
verified knowledge, reusable procedures, follow-ups,
validation evidence, and evolution candidates, then let the record go.

## Machine-Readable State

Structured JSON companion state is optional until graph or harness automation
proves a stable schema. Markdown task records are canonical.
