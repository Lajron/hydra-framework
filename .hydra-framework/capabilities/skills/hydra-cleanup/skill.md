# Hydra Cleanup Skill

## Capability

Review and improve the Hydra framework itself: its canonical files, task and
knowledge state, capabilities, workflows, validation material, documentation,
and generated provider surfaces. Find material that has no current reason to
exist or costs tokens and maintenance without preserving useful meaning.

This skill is proposal-first. It may apply approved changes in the same
session, but never silently deletes, rewrites, or self-modifies.

## Procedure

1. Establish a bounded scope from the user's request. Inspect nearby references
   and ownership before judging an item. The skill may inspect surrounding
   repository files, but changes outside Hydra-owned material need explicit
   scope.
2. Trace the selected subject area across its consumers in one pass: canonical
   sources, related capabilities or workflows, generated provider surfaces,
   references, and the relevant `project-wiki/hydra-framework/` page. Combine
   related cleanup and documentation changes into one reviewable proposal
   batch instead of repeating discovery for each surface. Do not update a wiki
   page merely because it is nearby; include it when the inspected material
   changes or clarifies what the page promises.
3. Read the relevant source-of-truth and, before proposing deletion from
   Hydra's machinery, read `.hydra-framework/repo/knowledge/silent-failure-modes.md`.
4. Look for stale, empty, duplicated, contradictory, misleading, pointless,
   or unnecessarily verbose material across any file type, including comments,
   descriptions, metadata, examples, scripts, adapters, and wiki content.
5. Classify each finding:
   - `safe to remove`: clearly obsolete, empty, redundant, misleading, or
     meaningless, with no required behavior or evidence lost.
   - `needs discussion`: potentially useful, ambiguous, or dependent on an
     unresolved source-of-truth or compatibility question.
   - `preserve`: carries a current constraint, decision, rationale, provenance,
     navigation role, validation contract, or non-obvious behavior.
6. Prefer consolidation over duplication. Keep the complete explanation in one
   canonical location and replace copies with short pointers when discovery and
   provider requirements still work. Fix canonical capability files before
   regenerating provider adapters; do not hand-edit generated surfaces.
7. Prefer meaning-preserving compression over terse writing. Shorten unique
   prose only when the same rule, exception, rationale, or example remains
   clear to an agent. Do not use character count alone as the deletion test.
8. Present reviewable batches. For every batch, show the reason, each affected
   path and item, the proposed action or before/after shape, uncertainty,
   approximate token or maintenance savings when estimable, and validation.
   Wait for explicit approval before editing. Approved batches may be applied
   in the same session; rejected and unresolved findings remain visible.
9. After an approved batch, run the narrowest relevant validation, export
   adapters when canonical capability files changed, and check for broken
   references or drift.
10. Record task-specific findings and decisions in the active task record. If a
   new pattern is reusable, propose a separate skill improvement; update this
   skill only with explicit approval and preserve its proposal, safety,
   source-of-truth, and validation rules.

## Output

Return grouped proposals under `safe to remove`, `needs discussion`, and
`preserve`. Do not bury deletions in a general review. End an approved batch
with changed files and validation evidence; if no concrete reduction is found,
say `Lean already. Ship.`

## Boundaries

- Do not remove or shorten content merely because it is correct, detailed, or
  repeated in a provider surface that genuinely needs a generated copy.
- Do not delete safety, validation, accessibility, migration, data-loss,
  provenance, or failure-detection material unless its replacement is explicit
  and verified.
- Do not resolve conflicting canonical sources by guessing. Report the conflict
  and identify the evidence needed.
- Do not edit generated adapters directly.
- Do not turn project-specific observations into universal skill rules without
  confirming they generalize.
