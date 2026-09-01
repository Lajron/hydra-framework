---
title: Operational Readiness
status: active
created: 2026-07-29
owners:
  team: hydra
certainty: inferred
provenance:
  sources:
    - .hydra-framework/capabilities/workflows/task-lifecycle.md
    - .hydra-framework/repo/knowledge/task-step-state.md
---

# Operational Readiness

## Purpose

Operational readiness is the Execution Harness check Hydra performs before meaningful execution so an agent does not discover preventable blockers halfway through a task.

Readiness is not a replacement for planning. It answers whether the local or project context is suitable for the next phase of work.

## Non-Trivial Tasks

For persisted non-trivial tasks, readiness is required.

A task is non-trivial when losing the current conversation would make the next agent waste meaningful tokens or risk doing the wrong thing. This includes work with repository changes, canonical Hydra changes, blockers, handoff, interruption risk, multi-session scope, unclear validation, or team visibility needs.

Small read-only or one-shot low-risk tasks may mark readiness as `not-required`.

## Minimum Fields

A readiness record must identify:

- readiness status
- branch and working-tree assumptions
- relevant canonical docs or `none identified`
- required dependencies, services, generated artifacts, and private local requirements
- blockers and assumptions
- expected validation command or evidence

## Certainty Discipline

A readiness result may be:

- `ready`: no known blocker
- `ready-with-assumptions`: execution can proceed after stated assumptions
- `blocked`: a concrete blocker prevents reliable execution
- `not-required`: task is too small or read-only

Do not mark a task ready by ignoring unknowns. If an unknown can affect correctness, record it as an assumption or blocker.

## Scope

Operational readiness is a Hydra core concept and an Execution Harness responsibility.

Project-specific checks belong in project or local configuration. Examples include service names, ports, package managers, container names, browser tooling, deployment targets, and credentials.

## Relationship To Validation

Readiness happens before or during planning.

Validation happens after a step or task changes something.

Both should preserve evidence, but neither should store raw conversations.
