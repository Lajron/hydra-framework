---
name: hydra-reflection-absorb
description: Select reflection packets in scope or past their Held-Until date, propose an outcome for each, and drain approved ones into canonical state or deletion.
---

# Reflection Absorb Skill

## Capability

Drain packets from `evolution/reflections/` into a terminal outcome:
deletion, a task follow-up, an `evolution/candidates/` record, an
`evolution record` entry, or an owner-approved canonical edit. Anyone may run
an absorb pass; this skill does not imply a designated reviewer or a review
hierarchy.

## Trigger

- The owner asks for an absorb pass, with or without a named scope.
- The per-prompt state pointer block reports a non-empty reflection queue and
  the owner wants it drained.
- A packet has passed its `Held-Until:` date.

## Procedure

1. Read `evolution/reflections/README.md` for the current packet contract
   and terminal-outcome list.
2. **List filenames first.** Run a directory listing of
   `evolution/reflections/`, not a read of every file. Select only packets
   in the owner's requested scope; with no scope given, take the oldest few
   by `Created:` plus any packet past its `Held-Until:` date. Do not read
   the whole directory's contents up front. That defeats the point of the
   one-file-per-packet layout.
3. Read only the selected packets.
4. Produce an absorb proposal grouped by outcome, using this destination
   map:
   - no reusable signal → delete
   - one more observation needed → hold, with a dated `Held-Until:`
   - task-scoped follow-up → the relevant record in
     `tasks/personal/<owner>/`
   - framework improvement proposal → `evolution/candidates/<date>-<topic>.md`
   - intentional local divergence → `hydra.py evolution record`
   - verified repository fact → `repo/knowledge/`
   - governing choice → its canonical owner in `core/`, `repo/knowledge/`,
     or `capabilities/`
   - reusable procedure → `capabilities/skills/` or
     `capabilities/workflows/`
5. Apply the promotion bar before proposing anything beyond hold or delete: a
   packet needs at least one of: repeated occurrence across sessions or
   people, clear validation evidence, direct maintainer confirmation, or an
   accepted change that already requires the update.
6. **Wait for owner approval before editing any shared state**, including
   deleting a packet. "Owner" means whoever owns the shared state being
   changed, not a designated reviewer or lead. Never suggest otherwise.
7. After an approved absorption, delete the packet. Do not move it to a
   second directory or an archive location; Git history is the archive.
8. Run `hydra.py validate` (and `ref index` first, if the outcome added an
   enveloped object) after every absorbed packet.
9. Report, per packet: its outcome, every shared file changed, and the
   validation run.

## Output

Report, per packet, its outcome, every shared file changed, and the validation
run.

## Boundaries

- Never read raw transcripts or telemetry logs as part of an absorb pass
  without the owner's explicit request.
- Never turn private scratch into shared state by reference. If a proposed
  outcome depends on `.hydra-framework.local/` content, inline the safe
  durable fact instead of citing the path.
- Never accept an evolution candidate, rule change, or knowledge edit on the
  owner's behalf without their approval.
- Never keep an absorbed packet as a second archive copy.
- Do not read every packet in the directory when the owner gave a scope.
  read only what is in scope, plus anything past its `Held-Until:` date.

## Validation Expectations

`hydra.py validate` clean after each absorbed packet. If the outcome added or
changed an enveloped object (a knowledge unit, a skill's `metadata.yaml`),
run `hydra.py ref index` before `validate`.

## Related

- `.hydra-framework/evolution/reflections/README.md`
- `.hydra-framework/capabilities/skills/session-reflection/skill.md`
