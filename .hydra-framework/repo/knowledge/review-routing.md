---
title: Review Routing For Shared Hydra State
status: active
owners:
  team: hydra
certainty: confirmed
provenance:
  sources:
    - .hydra-framework/core/placement-rules.md
    - .hydra-framework/engine/src/hydra_engine/identity/schema_versions.py
    - .github/CODEOWNERS
---

# Review Routing For Shared Hydra State

A change to `.hydra-framework/` shared state (`repo/knowledge/`,
`capabilities/`, `core/`, engine code) needs a reviewer who
actually owns the area, not an ambient "someone will look at it." This file
names how that reviewer is found.

## The Signal Is Already In The Object

Every Hydra object — every flat knowledge file, capability, and engine
module with an envelope — already declares `owners:` (team and, optionally,
`person`) as a required field. That field is the review-routing signal: the
object's own frontmatter names who is responsible for judging a change to
it. There is no separate reviewer registry to keep in sync with the objects
it describes, because keeping two records of the same fact was exactly what
caused the drift `placement-rules.md`'s "Source Of Truth" rule exists to
prevent.

This deliberately does not add a `Reviewer:` field to any object, for a
reason that generalizes across every governed queue in this repository: a
named-reviewer field imposes a team hierarchy the framework does not
otherwise encode, and who actually reviewed a change is recorded by the
commit or PR that merged it — Git already owns that fact.

## This Repository's Routing

`.github/CODEOWNERS` maps the shared-state paths in this repository
(`.hydra-framework/`, `project-wiki/`) to their current owning reviewer, so a
pull request touching them requests the right person automatically. That
mapping names real identities, which is why it lives in `.github/` rather
than in `.hydra-framework/` itself: `owners: team: hydra` in an object's
frontmatter is portable base-seed state, copied unchanged into every
repository this framework runs in (the same distinction `state-tiers.md`
draws for owner slugs), while a GitHub username or team handle is specific to
*this* repository's people and would be wrong the moment the seed is copied
elsewhere. A repository adopting Hydra should write its own `.github/
CODEOWNERS` (or the equivalent for its own code host) mapping its shared
state paths to its own reviewers, using this file's mapping as the pattern to
follow rather than the values to copy.

## Proposing A Change

See `repo/knowledge/procedures.md`'s "Propose A Hydra Framework Change"
section for the weight a given change needs before it reaches review.
