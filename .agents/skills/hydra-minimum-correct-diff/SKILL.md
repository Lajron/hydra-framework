---
name: hydra-minimum-correct-diff
description: Use when implementing, refactoring, or fixing code where avoiding unnecessary implementation surface matters.
---

# Minimum Correct Diff Skill

## Capability

Choose and implement the smallest correct change that satisfies the task after understanding the touched flow.

This skill reduces code, token, review, and maintenance cost by avoiding speculative implementation surface. It is not a license to skip comprehension, validation, security, accessibility, or data-loss handling.

## Procedure

1. Read the request and the code path the change touches. Trace the real flow before choosing a solution.
2. Stop at the first rung that correctly satisfies the task:
   - The behavior does not need to be built: explain the skip briefly and do not edit.
   - The repository already has a helper, type, pattern, script, or workflow: reuse it.
   - The standard library, framework, database, shell, browser, or platform already provides it: use that.
   - An installed dependency already covers it: use the existing dependency instead of adding one.
   - A one-line or local change is correct: prefer it over new files, abstractions, or configuration.
   - Otherwise write the minimum implementation that works.
3. For bug fixes, find the shared root cause. Search callers of the function or workflow being changed and fix the common path when that is the smaller correct repair.
4. Preserve non-negotiables: trust-boundary validation, security, data-loss prevention, accessibility, migration safety, concurrency correctness, and explicitly requested behavior.
5. Leave the smallest useful validation evidence for non-trivial logic: an existing test, a targeted new test, a smoke check, or a direct validation command. A passing check proves less than it appears to; when the change touches the task contract, the module format, the adapter exporters, or a downstream Hydra copy, read `.hydra-framework/repo/knowledge/silent-failure-modes.md` and confirm the specific failure it warns about is not the one you just introduced.
6. If a deliberate simplification has a known ceiling, record the ceiling and revisit trigger in the task record or the repository's normal debt marker. Use code comments only when the limitation would be invisible to future maintainers.

## Output

Report the files changed, the validation evidence, and any intentionally skipped implementation surface. Keep the explanation proportional to the change unless the user asks for deeper reasoning.

## Boundaries

- Do not add unrequested abstractions, dependencies, generated scaffolding, provider adapters, or configuration.
- Do not shrink canonical Hydra knowledge by lossy rewriting. Reduce loaded context and implementation surface instead.
- If the user explicitly asks for the fuller design after the smaller option is named, implement the requested design without repeating the challenge.
