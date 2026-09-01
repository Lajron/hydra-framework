---
name: hydra-repository-inspection
description: Inspect repository structure, Hydra docs, active tasks, and relevant knowledge before non-trivial repo work.
---

# Repository Inspection Skill

## Capability

Perform scoped repository discovery and preserve verified findings.

## Procedure

1. Start with cheap directly relevant reads.
2. Prefer `rg` and existing manifests.
3. Avoid broad scans unless they materially improve correctness.
4. Record verified durable facts in `repo/knowledge/`.
5. Record uncertain observations privately with `hydra.py note "<observation>"`. Promote one into `repo/knowledge/` with a stated certainty only once it is verified.

## Output

Report the scoped repository structure, verified conventions, relevant active
work, and any uncertain observations kept private.

## Boundaries

- Do not perform broad scans when cheap, directly relevant reads answer the question.
- Do not promote uncertain observations into shared knowledge. Keep them private until verified.
