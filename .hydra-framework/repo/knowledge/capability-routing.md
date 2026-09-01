---
title: Capability Routing
status: active
created: 2026-07-29
owners:
  team: hydra
certainty: inferred
provenance:
  sources:
    - AI_SYSTEM.md
    - .hydra-framework/repo/knowledge/operational-readiness.md
---

# Capability Routing

## Purpose

Capability routing helps Hydra choose the smallest adequate agent, model, tool, or workflow for the job while remaining provider-neutral.

Hydra should route by task risk and required capability, not by vendor identity.

## Routing Factors

Consider stronger reasoning, broader context, or additional review when work involves:

- architecture changes
- large refactors
- concurrency, distributed state, security, data loss, or migrations
- unclear requirements
- high blast radius
- cross-module contracts
- low test coverage
- conflicts between sources
- stale, uncertain, or disputed canonical knowledge
- high context pressure or token-budget constraints

Use lighter execution when work is:

- narrow
- well specified
- covered by tests
- local to one module
- mechanical or repetitive
- easy to validate

## Subagent Sizing

Use subagents or mini-agents when focused parallel judgment, independent validation, source review, or summarization reduces risk or main-context load.

Size dispatch conservatively:

- no subagent for narrow, local, low-risk changes with direct validation
- one focused subagent for source audit, security review, fresh validation, or domain-specific checking
- multiple subagents only for high-risk, ambiguous, cross-domain, or contested work where the coordination cost is justified

Subagents should receive scoped canonical context, a bounded task, expected output shape, and explicit collection criteria.

## Package Prompt Routing

Knowledge packages may provide `routing.yaml` metadata with keywords, a state
pointer, and `routes:`. Prompt-time routing may use this metadata to point an
agent at package state and, when a route matches the task, that route's
scoped units before broad repository search.

Routing output should stay small: it should identify what to read, not load the
package contents. This preserves the cost/token policy while making documented
packages easier to discover.

## Fresh Validation

Fresh validation is appropriate when:

- authoring context may bias review
- changes affect framework rules, adapter generation, hooks, memory, security, migrations, or cross-module contracts
- validation requires an independent read of changed files or source evidence
- a task is high-impact and automated tests are insufficient

Fresh validators should inspect the current repository state and relevant canonical docs, not raw conversation history.


## Minimum Correct Diff

For implementation tasks, route to the smallest correct diff after scoped comprehension. The ladder itself is defined once in the `minimum-correct-diff` skill (`capabilities/skills/minimum-correct-diff/skill.md`) and is not restated here.

Routing choice:

- Use `minimum-correct-diff` for implementation work where over-building is likely.
- Use `complexity-review` when reviewing an existing diff or module specifically for deletions and simpler replacements.

The ladder reduces code and token pressure, but it never removes validation, security, accessibility, migration safety, or data-loss protection.

## Cost And Token Factors

Routing should account for input tokens, cached-input tokens, output tokens, reasoning effort, latency, and tool-call cost.

Before adding always-loaded instructions, prefer just-in-time loading, smaller provider surfaces, scoped references, and smaller implementation surface. Token-saving claims should be measured when they affect shared framework policy.

When a debugging loop repeats the same command, tool call, error class, or failed assumption across 2-3 attempts, route away from normal retry behavior. The next step should be a concise evidence summary plus a changed hypothesis, narrower validation command, or human escalation.

When validation or command output is large, route through targeted inspection first: failing command, exit code, relevant error lines, nearest useful stack frame, and exact literals. Do not spend context on full logs unless the full log is required evidence.

Spend or token monitoring should start with provider-neutral counters and local/private records where possible: request count, input tokens, cached-input tokens, output tokens, reasoning tokens, tool-output size, retry count, loop halts, and estimated cost by task or workflow. Use those measurements to decide whether a compression tool, gateway, or model-routing layer is justified.



## Effort Routing

Hydra routes model effort as a capability budget. Shared records should name the
budget, not a provider parameter:

- `minimal`: deterministic routing, formatting, simple extraction, or log triage
- `low`: narrow local edits, summaries, and directly validated changes
- `standard`: ordinary implementation, review, and documentation work
- `high`: architecture, migrations, security, cross-module contracts, or unclear requirements
- `max`: exceptional high-risk work where smaller budgets have proved inadequate

Subagents should usually use `minimal`, `low`, or `standard` unless their bounded
task is explicitly high-risk. A cheaper model or lower effort budget is useful
only when the task boundary, expected output, and validation check are narrow.

## Provider Neutrality

Canonical Hydra records should describe capability classes, not specific provider products.

Examples:

- `fast-default`
- `deep-reasoning`
- `large-context`
- `tool-heavy`
- `review-focused`
- `local-private`

Project adapters may map these classes to concrete providers, models, tools, or local workflows.

## Validation

Routing decisions should be revisited when evidence shows:

- repeated failures
- excessive cost or latency
- insufficient context
- unnecessary coordination overhead
- token savings that reduce correctness
- better local validation makes a smaller capability adequate
