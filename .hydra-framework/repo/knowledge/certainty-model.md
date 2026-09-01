---
title: Certainty Model
status: active
created: 2026-07-29
owners:
  team: hydra
certainty: confirmed
provenance:
  sources:
    - AI_SYSTEM.md
    - .hydra-framework/repo/knowledge/memory-governance.md
---

# Certainty Model

Hydra must separate confirmed facts from assumptions.

This prevents models from turning guesses, stale notes, extracted artifacts, or previous attempts into trusted engineering memory.

## Certainty States

- `confirmed`: verified by source of truth, implementation, tests, maintainer answer, accepted rule, or reproducible evidence.
- `inferred`: likely conclusion based on available evidence, but not directly confirmed.
- `assumed`: temporary working assumption used only after being stated explicitly.
- `unresolved`: consequential uncertainty that needs an answer.
- `conflicting`: multiple sources disagree.
- `superseded`: previously useful but replaced by newer evidence, rules, or implementation.
- `rejected`: reviewed and intentionally not used.

## Usage Rules

- State uncertainty before dependent work.
- Do not promote inferred or assumed claims as confirmed facts.
- Record consequential unresolved questions in the relevant package, task, or pending area.
- Prefer source links, evidence notes, and validation results over vague confidence.
- When a previous attempt had a known mistake, mark its conclusions as superseded or previous-attempt context.

## Promotion Rule

Canonical knowledge may include uncertainty, but it must label the uncertainty.

Example:

```yaml
certainty: conflicting
status: needs-confirmation
```

Do not hide uncertainty in prose where future agents might miss it.
