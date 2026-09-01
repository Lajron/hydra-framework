# Telemetry Evidence Absorb Skill

## Capability

Drain `open` packages from `repo/telemetry/packages/` into a terminal
outcome: a knowledge file, a canonical rule change, a task follow-up, an
`evolution/candidates/` entry, a `superseded` pointer to a newer
re-measurement, or `rejected` with one sentence why. Anyone may run an
absorb pass; this skill does not imply a designated reviewer or a review
hierarchy. Unlike `reflection-absorb`, no package is ever deleted. See
`repo/telemetry/README.md`'s Terminal Outcomes section for why.

## Trigger

- The owner asks for a telemetry evidence absorb pass, with or without a
  named scope.
- The per-prompt state pointer block reports open telemetry evidence
  packages and the owner wants them drained.
- `hydra.py validate` surfaces a staleness advisory for an aging `open`
  package.

## Procedure

1. Read `repo/telemetry/README.md` for the current package contract,
   status vocabulary, and terminal-outcome list.
2. **List directory names first.** Run a directory listing of
   `repo/telemetry/packages/`, not a read of every package. Select only
   `open` packages in the owner's requested scope; with no scope given,
   take the oldest few by `Created:`. Do not read every package's files up
   front. That defeats the point of the one-package-per-question layout.
3. For each selected package, read only its `overview.md` first (`##
   Question` and `## Findings`); read `metrics.json` and
   `gate-attestation.json` only if the finding's derived numbers need
   checking directly.
4. Produce an absorb proposal grouped by outcome, using this destination
   map:
   - durable repository fact → `repo/knowledge/`
   - forces a rule → its canonical owner in `core/`, `repo/knowledge/`, or
     `capabilities/`
   - framework-level proposal → `evolution/candidates/<date>-<topic>.md`
   - work to schedule → a task record or a roadmap item
   - re-measured later with a materially different result → a new package
     carrying `supersedes:`; this package becomes `status: superseded` with
     `superseded_by:` pointing at it
   - not actionable → `status: rejected`, one sentence why in `##
     Absorption`
5. Apply the promotion bar before proposing anything beyond `rejected`: a
   finding needs at least one of: a passing `gate-attestation.json`
   (`verdict: pass`) less than `STALE_OPEN_TELEMETRY_EVIDENCE_DAYS` old,
   corroboration from a second package or source, or direct maintainer
   confirmation.
6. **Wait for owner approval before editing any shared state**, including
   changing a package's `status`. "Owner" means whoever owns the shared
   state being changed, not a designated reviewer or lead. Never suggest
   otherwise.
7. After an approved absorption, edit the package's `status` field and fill
   in `## Absorption` naming the real artifact (or, for `rejected`, the one
   sentence why). Do not delete the package and do not move it to a second
   directory. See Terminal Outcomes above.
8. Run `hydra.py ref index` then `hydra.py validate` after every absorbed
   package, since changing `status` (and adding `superseded_by:` where it
   applies) changes the object's envelope.
9. Report, per package: its outcome, every shared file changed, and the
   validation run.

## Output

Report, per package, its outcome, every shared file changed, and the validation
run.

## Boundaries

- Never read raw `.hydra-framework.local/telemetry/` rows as part of an
  absorb pass. A package's `metrics.json` and `overview.md` are already the
  bounded, safe-to-read surface; there is nothing legitimate to check
  further back than that.
- Never turn private capture into shared state by reference. If a proposed
  outcome would need something not already in the package, that is a signal
  the finding needs a new, better-measured package, not a citation into
  `.hydra-framework.local/`.
- Never accept a knowledge edit, rule change, or candidate on the owner's
  behalf without their approval.
- Never delete a package, absorbed or not.
- Do not read every package in the directory when the owner gave a scope.
  read only what is in scope, plus anything the staleness advisory flagged.

## Validation Expectations

`hydra.py ref index` then `hydra.py validate` clean after each absorbed
package. If the outcome added a new knowledge file or a second telemetry
evidence package, treat that new file the same way: index, then validate.

## Related

- `.hydra-framework/repo/telemetry/README.md`
- `.hydra-framework/capabilities/skills/reflection-absorb/skill.md`
