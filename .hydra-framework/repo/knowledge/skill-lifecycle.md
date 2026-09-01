---
title: Skill Lifecycle
status: active
created: 2026-07-29
owners:
  team: hydra
certainty: inferred
provenance:
  sources:
    - .hydra-framework/capabilities/
    - AI_SYSTEM.md
---

# Skill Lifecycle

## Purpose

Hydra skills should capture repeated procedures that are useful enough to maintain.

A skill is not a persona. It is an operational capability with a clear trigger, inputs, procedure, dependencies, and validation expectations.

Agents own focused judgment roles. Skills own reusable procedure. A skill may route to an agent or subagent when judgment is needed, but it should not duplicate persona instructions or broad role behavior.

## Package Shape

A skill package should define:

- capability: what reusable procedure the skill provides
- trigger: when the skill should be used
- inputs: required context, files, services, or user-provided facts
- outputs: expected artifacts, findings, or validation evidence
- procedure: ordered steps with clear stop and escalation points
- dependencies: tools, scripts, services, provider features, or private local requirements
- references: focused canonical knowledge or templates to load just in time
- examples or evals: representative cases when useful
- validation expectations: how successful use is checked
- provider requirements: adapter-specific behavior only when unavoidable

References should be loaded only when relevant to the current task. Avoid always-on skill corpora that increase context cost without improving execution.

## Lifecycle

`observed-repeat -> candidate -> drafted -> used -> validated -> active-or-retired`

## Promotion Criteria

Create or promote a skill when:

- the workflow has repeated at least enough to show stable shape
- the procedure prevents meaningful re-derivation
- the inputs and expected outputs are clear
- the skill can stay provider-neutral or declare adapter requirements
- maintenance cost is lower than repeated improvisation
- validation can be described

Do not promote a skill just because a task was important once.

Use evidence-based YAGNI for skill promotion. Unsupported recommendations, runbooks, abstractions, tests, or agent dispatch patterns should be recorded as pending or evolution candidates rather than silently promoted.

## Retirement

Retire or supersede a skill when:

- the repository no longer uses the workflow
- the procedure has drifted from reality
- a canonical workflow replaces it
- it adds coordination overhead without improving outcomes

Retired skills should preserve useful lessons but stop presenting themselves as active instructions.
