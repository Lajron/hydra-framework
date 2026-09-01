---
name: hydra-session-reflection
description: Capture one sanitized, durable observation about using this framework as a reflection packet, or say why none is warranted.
---

# Session Reflection Skill

## Capability

Capture one sanitized, durable observation about using this framework from
the session's own already-loaded context as a reflection packet in
`evolution/reflections/`, or determine that no packet is warranted and write
nothing.

## Trigger

- The session hit friction, confusion, or a gap in a Hydra rule, knowledge
  file, skill, or workflow that is not itself the task's outcome.
- `hydra.py task complete` is about to run and the session produced framework
  friction the task record's own outcome does not capture. This is a
  trigger, not a requirement. Filing at task completion is a natural moment,
  not the only valid one.

## Procedure

1. **Two-stage rule first.** A packet is never a first draft. If the
   observation is still half-formed, run `hydra.py note "<title>"`
   privately and stop. A packet is written only once an observation could
   survive being stated sanitized.
2. **Reflect only from what is already loaded.** Use the session's own
   context and command output already produced in it. Never ask the owner to
   paste a transcript. Never read provider transcripts, raw command logs, or
   telemetry JSONL unless the owner explicitly asks for that investigation.
3. **Bounded telemetry only, if it helps.** If a report would materially
   strengthen the packet, use `hydra.py measure-context` or the
   `hook-token` / `summarize-log` command family, never a raw log file.
4. **The bar to file at all.** The observation must be durable: framework
   friction, a rule that misled, repeated confusion, a confirmed gap,
   validation evidence, or token-cost pressure. If there is no durable
   signal, say so and write nothing. This step exists on its own, not as a
   closing aside, because "write something anyway" is the failure this skill
   is designed against.
5. Read `evolution/reflections/README.md` for the current packet contract
   before writing, in case it has changed.
6. Write exactly one packet at
   `evolution/reflections/<YYYY-MM-DD>-<slug>.md` from
   `evolution/templates/reflection-packet.md`. Set `Author:` to the resolved
   owner slug, `Status: open`, and both `Created:`/`Updated:` to today. Do
   not set `Held-Until:`. It belongs only to `Status: held`.
7. **Sanitize before writing**, against the packet rules in the README: no
   raw transcript, no raw command log, no secrets or credential-like output,
   no private machine path unless the path itself is the subject, no
   citation to `.hydra-framework.local/`, no unsupported claim that a Hydra
   rule or capability is wrong, short reduced facts only.
8. Report the packet path, or report that no packet was created and why.

## Output

Report the packet path, or report that no packet was created and why.

## Boundaries

- No raw conversation history in a packet.
- No private paths, secrets, or credential-like output.
- No citation to `.hydra-framework.local/`. Inline the safe durable fact
  instead.
- Do not edit canonical knowledge, core rules, capabilities, or evolution
  candidates from this skill. Capture writes one file only; absorption is
  `capabilities/skills/reflection-absorb/`.
- Do not append to a monolithic reflection file. One packet, one file.
- One packet per session at most.

## Validation Expectations

`hydra.py validate` should stay clean after writing a packet: required
fields present, `Status` in `{open, held}`, no `Held-Until:` on an `open`
packet, all three required sections present, and the packet under the token
ceiling in `evolution/reflections/README.md`.

## Related

- `.hydra-framework/evolution/reflections/README.md`
- `.hydra-framework/evolution/templates/reflection-packet.md`
- `.hydra-framework/capabilities/skills/reflection-absorb/skill.md`
