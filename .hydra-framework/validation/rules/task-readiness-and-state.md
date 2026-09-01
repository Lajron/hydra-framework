# Validation Rule: Task Readiness And State

Status: active
Created: 2026-07-29
Updated: 2026-07-30
Certainty: confirmed

## Purpose

This rule records what task-record validation covers today, and what is
deliberately still unchecked.

## Implemented

`hydra.py validate` fails when an active task record is missing any field in
`REQUIRED_TASK_SECTIONS`. The field list is stated once in prose in
`.hydra-framework/capabilities/workflows/task-lifecycle.md`; this rule does not
restate it.

Validation also checks that the prose description, the template in
`tasks/templates/task.md`, and the executable list agree with each other, so the
contract cannot drift between the three places that express it.

## Not Yet Implemented

These need judgment a string check cannot supply, so they stay open rather than
being enforced badly:

- A blocker being understandable to another agent or human, not just present.
- Completed steps actually carrying validation evidence rather than a placeholder.
- Superseded steps naming the plan or task state that replaced them.
- Private local state not being referenced as a shared source of truth.
- Structured companion state agreeing with the Markdown record.

## Non-Goals

- Requiring structured state for every trivial task.
- Requiring JSON companion state before a stable schema is justified.
- Requiring a specific provider, model, or tool.
- Validating raw conversation history.

## Open Schema Question

The exact machine-readable task-state schema is unresolved. Markdown task records
are canonical; JSON companion files remain optional until graph or harness
automation proves a stable schema.
