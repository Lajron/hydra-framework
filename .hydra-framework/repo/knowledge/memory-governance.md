---
title: Memory Governance
status: active
created: 2026-07-29
owners:
  team: hydra
certainty: reviewed-docs
provenance:
  sources:
    - AI_SYSTEM.md
    - .hydra-framework/core/placement-rules.md
---

# Memory Governance

## Purpose

Hydra memory preserves durable meaning that helps future agents continue work accurately.

Canonical memory is Git-tracked shared state under `.hydra-framework/`: knowledge,
intake promotion records, module definitions, validation evidence, and evolution
candidates.

Task records are **not** canonical memory. They are personal work state: tracked
so they survive and can be inherited, but removed on completion, because what a
finished task *meant* belongs in its canonical owner. A record is scaffolding
for work in progress, not a memory of it. The placement rules set this boundary.

The consequence for evidence: validation evidence that proves an accepted change must live in the knowledge file it supports, not only in the record that produced it. Evidence that merely shows a step ran is scaffolding and goes with the record.

Raw conversation history is not canonical memory.

## Boundaries

Store shared durable memory in `.hydra-framework/` when it describes the repository.

Store personal in-flight work state in `.hydra-framework/tasks/personal/<owner>/`.

Store private memory in `.hydra-framework.local/` when it contains credentials, secrets, local paths, personal notes, planning, open questions, triage judgments, private tool mappings, hook trust state, or experimental backend configuration.

A shared file must never cite a private one. See `core/placement-rules.md`.

Provider-local auto-memory — for example Claude Code's per-project memory, or
an equivalent Codex feature — is a fourth kind of state outside all three
tiers: it lives outside this repository, so Hydra does not create, seed, back
up, or validate it. `repo/knowledge/state-tiers.md` names its shape and
promotion path. Treat it as non-authoritative personal convenience state,
governed by this file's own model-discretion-capture rule above, until a
durable claim from it is promoted into `repo/knowledge/`, `core/`, or a
personal task record.

External memory systems may assist recall, search, or coordination, but they do not own canonical Hydra framework meaning.

## Capture Tiers

Hydra distinguishes capture guarantees:

- Deterministic capture: scripts, validation checks, hooks, or explicit file edits record known events or state transitions.
- Tool-mediated capture: an agent intentionally invokes a tool or workflow to write a bounded memory artifact.
- Model-discretion capture: a model may choose to recall or write through an optional memory interface.

Critical task state, accepted rules, constraints, validation evidence, and supersession records require deterministic or explicit tool-mediated capture. They must not rely only on model-discretion memory.

## Governed Records

Durable memory records should make ownership and validity clear:

- provenance: where the fact, rule, or evidence came from
- attribution: who or what accepted the record when known
- namespace: which repository, module, task, or domain the record applies to
- temporal status: created date, current status, and supersession when relevant
- certainty: confirmed, inferred, reviewed-docs, or pending when useful
- access boundary: shared, private, credential-bearing, or external-reference-only

## Supersession

When memory changes, prefer explicit supersession over silent replacement.

Archived or superseded knowledge should preserve the durable lesson and point at the current authority. Temporary raw notes should not be promoted only to keep history.

## Secrets

Secrets, credentials, tokens, private backend configuration, and vault material must not be stored in shared Hydra memory.

Shared state may document that a private requirement exists, but the value and machine-specific setup belong outside Git.
