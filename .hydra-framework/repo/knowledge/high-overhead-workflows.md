---
title: High-Overhead Workflows
status: active
created: 2026-08-21
owners:
  team: hydra
certainty: confirmed
provenance:
  sources:
    - .hydra-framework/core/architecture.md
---

# High-Overhead Workflows

## Purpose

High-overhead workflows are Execution Harness controls that add isolation,
independent review, or explicit approval around risky work.

They are not the default way to do tasks. They are the framework's escalation
path when the normal loop does not sufficiently control a concrete failure mode.

## Selection Rule

Choose by risk and blast radius:

1. Name the failure mode.
2. Decide whether the likely failure is local and reversible, shared and
   disruptive, or destructive or sensitive.
3. Select the smallest workflow that addresses that failure mode.
4. Record the reason when the workflow is required or materially affects
   continuation.

Low-risk work stays in the normal loop: read relevant context, make the scoped
change, run surface-appropriate validation, and report evidence.

## Workflow Matrix

| Workflow | Recommended when | Required when | Usually unnecessary when |
| --- | --- | --- | --- |
| Isolated worktree | Parallel humans or agents need separation, a task spans branches, branch states must be compared, or long-running generated output would pollute the current checkout. | Multiple active execution contexts would write the same checkout, two branch states must coexist, or a risky migration needs rollback that must not depend on unstaged local work. | One agent is making a scoped change in a known working tree after checking relevant Git state. |
| Isolated execution environment | Commands install dependencies, mutate caches, call external services, run unfamiliar project scripts, or rely on private local setup. | Running unaudited code, untrusted tooling, migration experiments, commands with broad filesystem side effects, or anything that may write outside the repository or alter shared services. | Reviewed local scripts and ordinary validation commands have understood side effects. |
| Browser sandboxing | Browser automation may touch credentials, tenant state, payment-like flows, admin settings, production-like data, or third-party scripts. | Automation targets production, customer data, privileged sessions, payment flows, account settings, or destructive UI workflows. | Static local pages, mocked demos, or owner-run manual checks where Hydra is not driving the browser. |
| Multi-agent review | Broad architecture changes, provider adapter changes, task contract changes, security-sensitive behavior, or framework changes would benefit from a second perspective. | Shared default instructions, executable harness behavior, destructive automation, credential handling, provider permissions, or seed-promotion candidates with downstream blast radius are affected. | The edit is narrow, locally reversible, and directly covered by deterministic validation. |
| Validation agent | The authoring context may bias validation, validation requires reading a different source set than implementation, or a task touches multiple ownership areas. | High-risk framework contracts changed, especially task contracts, provider adapters, hooks, executable scripts, migration tooling, or trust-boundary behavior. | A deterministic local gate directly covers the change and there is no meaningful judgment step beyond reading the command result. |
| Destructive-command gate | A command may delete, overwrite, migrate, force-push, rewrite history, drop data, modify shared services, or change permissions. | The owner did not explicitly request the destructive action, the operation is irreversible, or the target cannot be confirmed from Git, scripts, or an external source of truth. | Commands are read-only, formatting-only, validation-only, generated-surface checks, or reversible edits inside the workspace. |

## Required Evidence

When a high-overhead workflow is required, record:

- the risk that triggered it
- the selected workflow
- the validation, approval, or review evidence
- rollback or continuation details needed by the next agent

For persisted tasks, use the task record's Readiness, Step State, Changed Files,
Validation, or Continuation Notes sections. For completed framework work,
put the evidence in the related knowledge doc. For private experiments,
keep it in `.hydra-framework.local/`.

## Local Overrides

Repository instructions, provider policies, and tool approval rules may be
stricter than this page. Follow the stricter rule first. Use this page for the
workflow choices those rules leave open.

## Sources

- `.hydra-framework/core/architecture.md`
