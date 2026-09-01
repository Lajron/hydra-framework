# Task Lifecycle Skill

## Capability

Maintain Hydra task records, readiness, step state, checkpoints, handoff, and completion for persisted non-trivial work.

Use this skill when work is non-trivial, interrupted, blocked, handed off, spread across sessions, or useful for team visibility.

## Procedure

1. Run `python3 .hydra-framework/scripts/hydra.py board` to see what is already in flight and who owns it. Records live in `.hydra-framework/tasks/personal/<owner>/`.
2. Decide whether persistence is required. Do not create formal state for trivial one-shot work.
3. For persisted work, create or update a Markdown task record from `.hydra-framework/tasks/templates/task.md`. The `/hydra-task-state` command wraps the helper that scaffolds it.
4. Fill in every required field. The field list is defined once in `.hydra-framework/capabilities/workflows/task-lifecycle.md`; read that rather than working from memory. The template's headings are the same contract in fill-in form.
5. Record readiness before execution, and update step state after meaningful progress. Move `Updated:` when you change the record. A generated record still full of template placeholders is worse than no record.
6. Create a checkpoint when work pauses, context is low, a blocker appears, a model handoff is likely, or another developer needs to continue.
7. To hand work over, run `task handoff <record> --to <owner>`. It moves the record and rewrites `Owner:` so the two never disagree. Then tell the person; moving a file is not telling them.
8. On completion, promote durable outcomes: verified knowledge, reusable procedures, follow-ups, validation evidence, evolution candidates. Then run `task complete <record> --outcome <path|none>`. The record is deleted; Git history is the archive.
9. Verify with `python3 .hydra-framework/scripts/hydra.py validate`, which fails on any missing required field.

## Output

- Task records and checkpoints must be factual, concise, and resumable.
- Do not store raw conversation history.
- Do not create disconnected competing task records for the same objective.
- Edit only your own records. Read anyone's.
- Keep planning, open questions, reactions, credentials, and machine paths out of records; those belong in `.hydra-framework.local/`. `hydra.py note "<title>"` is the fast way into a named private note.

## Boundaries

- Do not create disconnected competing task records. Update the existing record for the same objective instead.
- Do not store raw conversation history. Preserve concise facts and continuation state.
- Do not edit another owner's record. Use `task handoff` to change ownership.
