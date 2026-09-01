# Reflection Queue

This directory is a governed, shared, temporary review queue for sanitized
observations about using this framework — friction, useful behavior, repeated
confusion, or a gap someone noticed while doing real work. It is not canonical
knowledge, not raw memory, and not a personal notebook. It is governed the
way `core/placement-rules.md` requires any shared, temporary, churning queue
to be: every item answers a question about the repository, says who filed
it, and drains toward a terminal end state.

## When Not To Use It

If you already know the answer, file an `evolution/candidates/` improvement
record instead — that is the channel for a proposal about shared property.

If the thought is still half-formed, `hydra.py note "<title>"` privately.
No packet is a first draft; a packet is written only once a private note has
survived long enough to be stated sanitized (the two-stage rule).

This ordering is deliberate: the failure mode this queue is designed against
is over-filing, not under-filing.

## Packet Contract

Path: `evolution/reflections/<YYYY-MM-DD>-<short-slug>.md`. There is no
`pending/` subdirectory — presence in this directory *is* pending, and every
terminal outcome deletes the packet.

```markdown
# <YYYY-MM-DD> - <Short Title>

Status: open
Author: <owner-slug>
Created: <YYYY-MM-DD>
Updated: <YYYY-MM-DD>
Scope: <Hydra area or repository area>

## Observation

<What durable friction, useful behavior, repeated confusion, or gap was seen.
Two to five sentences. Reduced facts, not narrative.>

## Evidence

- <File paths, command results, validation evidence, or bounded telemetry
  report output. No raw logs, no transcripts.>

## Suggested Outcome

<What might follow, and what would justify promotion or deletion. The author
is not required to know the answer; "unsure, but this cost me an hour" is a
valid suggested outcome.>
```

Required header fields: `Status`, `Author`, `Created`, `Updated`, `Scope`.
Required sections: `## Observation`, `## Evidence`, `## Suggested Outcome`.
`Author:` is the only attribution field — there is no `Reviewer:` field, and
none should be added. Anyone may file a packet; anyone may absorb one. Who
absorbed it, and when, is recorded by the commit that deletes it.

### Status Vocabulary

A closed set of two values:

- `open` — filed, not yet drained. The default and the overwhelmingly common
  state. `Held-Until:` must not be present.
- `held` — deliberately kept because one more observation is needed.
  `Held-Until: <YYYY-MM-DD>` must be present.

`Held-Until:` is coupled 1:1 to `Status: held`; it is never present on an
`open` packet and never absent on a `held` one. `hydra.py validate` treats
either violation as an error.

## Packet Rules

- no raw transcript
- no raw command log
- no secrets or credential-like output
- no private machine path unless the path itself is the subject of the problem
- no citation to `.hydra-framework.local/`
- no unsupported claim that a Hydra rule, knowledge file, or capability is wrong
- short reduced facts only

## Terminal Outcomes

Every outcome deletes the packet. There is no `absorbed` status and no
archive directory — Git history is the archive.

- deleted as no reusable signal
- converted to a task follow-up in a task record
- promoted to `evolution/candidates/<date>-<topic>.md`
- recorded with `hydra.py evolution record` into `evolution/adaptations.md`
- promoted, after owner approval, into `repo/knowledge/`, `core/`, or
  `capabilities/`

## Telemetry Policy

Bounded reports only — `hydra.py measure-context` and the `hook-token` /
`summarize-log` command family where they apply. Never read raw monitoring
JSONL or provider transcript files to write or absorb a packet unless the
owner explicitly asks for that investigation.

## Drain Expectations

`hydra.py validate` emits advisory notes, never build failures, for:

- an `open` packet whose `Created:` date is older than the staleness
  threshold
- a `held` packet past its `Held-Until:` date
- queue depth above the readability backstop

These thresholds are `TEAM_TUNABLE_POLICY` in
`engine/src/hydra_engine/thresholds.py` — a team that works differently may
set them differently. They are notes, not failures: a check that blocks work
for bookkeeping is one people route around.

## Capture And Absorb

Two skills, not one. `capabilities/skills/session-reflection/` files a
packet; `capabilities/skills/reflection-absorb/` reads packets and, after
owner approval, drains them into a terminal outcome.
