---
title: Task Step State
status: active
created: 2026-07-29
owners:
  team: hydra
certainty: inferred
provenance:
  sources:
    - .hydra-framework/capabilities/workflows/task-lifecycle.md
    - .hydra-framework/tasks/templates/task.md
---

# Task Step State

## Purpose

Task step state lets Hydra resume non-trivial work after interruption, handoff, or context compression.

Human-readable task records are canonical Execution Harness state. A small structured companion artifact may exist when machine-readable continuation would reduce risk.

## Core Model

Persisted non-trivial tasks must make these fields visible in Markdown:

- readiness status
- branch or workspace assumptions
- relevant canonical docs
- required dependencies, services, generated artifacts, or private local requirements
- current stage
- active step
- next step
- completed steps
- blockers
- assumptions
- changed files
- validation evidence
- continuation notes

## Intent Snapshot

When a task begins or changes materially, capture a concise intent snapshot in the task record:

- the objective
- accepted constraints and explicit non-goals
- relevant canonical sources
- expected validation command or evidence
- assumptions that would change execution if disproven

The snapshot should preserve durable meaning, not raw prompt text.

## Validator Context Boundary

Validation evidence should be reproducible from repository state and named external systems where possible.

A fresh validator should receive scoped canonical context, task intent, changed files, and validation commands. It should not depend on the author's raw conversation history.

Validation records should include the command, date, and result. For failed validation, preserve the durable failure summary and next step rather than full noisy logs unless the log is the evidence.

## Suggested Step States

- `pending`: known but not started
- `in-progress`: actively being worked
- `blocked`: cannot continue without an external change or answer
- `validated`: completed and checked
- `superseded`: replaced by a newer plan or decision
- `skipped`: intentionally not executed

## Structured Companion

When useful, a task can include a structured file beside the task record, such as:

`<task-name>.state.json`

The schema is not yet fixed. Until Coordination Graph or Execution Harness automation proves a stable schema is useful, Markdown task records remain the source of truth and JSON companion files stay optional.

## Promotion Rule

Only durable outcomes should outlive the task:

- verified knowledge
- reusable procedures
- unresolved follow-ups
- validated improvement candidates
- validation evidence and bounded lifecycle facts

Do not preserve raw step-by-step conversation as memory.
