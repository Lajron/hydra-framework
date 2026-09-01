# Telemetry Evidence Packages

This directory is a governed, shared, temporary review queue for bounded
evidence derived from this repository's private telemetry corpus — one
measurement pass, made shareable. This file is the operative contract this
directory exists under; `hydra_engine.identity.object_families` registers
the `Telemetry` object family this depends on, and
`repo/knowledge/telemetry-redaction-contract.md` is the redaction contract
each package must pass.

It is not a shared event stream. Capture stays local-only, forever, under
`.hydra-framework.local/telemetry/`. Nothing here is a log excerpt, a raw
row, or a per-event object: a stream of individually committed rows never
stops growing, produces a diff nobody reviews, and propagates any sensitive
payload to every clone and downstream copy with no later deletion able to
recall it.

## When Not To Use It

If the observation has no numbers behind it — a piece of friction, a repeated
gap, a suggestion — file it in `evolution/reflections/` instead, or privately
with `hydra.py note "<title>"`. This queue is for a measured question about
telemetry, with a passing gate attestation behind it.

## Directory Layout

```
repo/telemetry/
  README.md                          this file
  templates/telemetry-evidence.md    fenced-block template to copy
  packages/
    <UniqueName>/
      overview.md            REQUIRED — the enveloped object
      metrics.json            REQUIRED — derived aggregates, scalars only
      gate-attestation.json   REQUIRED — verbatim `telemetry gate` output
```

Exactly these three files, no subdirectories. Copy
`templates/telemetry-evidence.md` for `overview.md`'s shape; `hydra.py
telemetry evidence create` mints all three from a real `telemetry gate` run.

## `<UniqueName>`

```
<YYYY-MM-DD>-<owner-slug>-<short-slug>
```

`<YYYY-MM-DD>` is the filing date and must equal `overview.md`'s `Created:`.
`<owner-slug>` is the filer's owner slug (the same slug
`tasks/personal/<owner>/` resolves from `HYDRA_OWNER` or `git config
user.email`) and must equal `overview.md`'s `Author:`. `<short-slug>` is a
non-empty lowercase `a-z0-9-` fragment naming the question. The date-plus-
owner combination is what makes the name collision-free: two people, or the
same person on two different days, cannot collide; the same person filing two
packages on the same day about the same question is a genuine duplicate.

`hydra_id` must end with the full directory name:
`hydra://telemetry-evidence/<UniqueName>`.

## `overview.md`

The standard object envelope, plus:

```markdown
---
hydra_id: hydra://telemetry-evidence/<UniqueName>
uid: <fresh uuid4>
schema_version: 3
kind: telemetry-evidence
title: <Short, Specific Title>
status: open
scope: base-seed
owners:
  individual: <owner-slug>
relations: []
provenance:
  sources:
    - .hydra-framework/repo/telemetry/packages/<UniqueName>/gate-attestation.json
---

# <Title>

Author: <owner-slug>
Created: <YYYY-MM-DD>
Window: <what span of local capture this measures, e.g. "2026-08-01 to 2026-08-28">
Corpus: <event count and kinds measured, e.g. "358 events across 5 kinds">

## Question

<The one question about this repository's runtime this package answers.>

## Findings

<Derived aggregates and short explanations. Structural evidence over
textual: counts, ratios, rates, field names, failure classes, short
sanitized snippets. No raw event rows, no transcript text, no file
contents, no `.hydra-framework.local/` path.>

## Method

<How `metrics.json` was produced — which `telemetry report` invocation or
derivation, over what window.>

## Absorption

<Filled in only once a status other than `open` is set: which knowledge
file, task, or candidate the finding fed, or why it was
rejected.>
```

`status` is the queue status — there is no second `Status:` prose line, a
simplification over the reflection and candidate queues, which have no
envelope of their own to carry it.

### Status Vocabulary

A closed set of four values:

- `open` — filed, not yet absorbed. The default, and the only non-terminal
  value.
- `absorbed` — a finding was drained into durable state. `## Absorption` must
  name the real artifact it fed (a knowledge file, a
  task record, or an `evolution/candidates/` entry).
- `superseded` — a later re-measurement replaced this package's findings.
  `superseded_by: hydra://telemetry-evidence/<newer>` is required (the same
  field name the existing dangling-reference check already validates for
  free).
- `rejected` — measured, judged not actionable. One sentence why, in
  `## Absorption`.

`hydra.py validate` rejects any other value.

## What May Cross From Private Into Shared

**Allowed:** derived aggregates (counts, sums, ratios, rates, distinct
counts); field *names* seen, never values; values of `captured verbatim`
fields that also pass the redaction contract's `contains_unsafe_content`
check; hashed ids only in `_hash` form, and only when a count will not do;
short sanitized snippets and short explanations; the gate attestation
verbatim.

**Forbidden:** any raw event row pasted into `metrics.json`; transcript text,
prompt text, command output, or file contents; any
`.hydra-framework.local/` path anywhere in the package; anything the
redaction contract's `contains_unsafe_content` check flags.

This reuses `hydra_engine.telemetry.redaction`'s executable contract rather
than inventing a second one, so a package inherits future redaction
improvements for free. `contains_unsafe_content` matches a bare `customer:`
or an absolute path even inside a code fence — describe sensitive paths and
customer-shaped examples generically in package prose instead of quoting
them.

`metrics.json` accepts only the aggregate report shape `hydra.py telemetry
report --json` emits: scalar counts and rates, per-kind counts, field-name
lists, and other named aggregate buckets. No arrays of objects, no raw
row-shaped maps, no `event_schema` key at any depth.

## Terminal Outcomes

Unlike `evolution/reflections/`, a terminal outcome here is a status value,
not file deletion. An absorbed, superseded, or rejected package stays in
`packages/` permanently — it is the durable record of a measurement this
repository already made, and deleting it would break the absorbing
knowledge file's citation. Only `open` packages are still
in-flight.

## Drain Expectations

`hydra.py validate` emits advisory notes, never build failures, for:

- an `open` package whose `Created:` date is older than the staleness
  threshold
- `open` queue depth above the readability backstop
- a `gate-attestation.json` whose `redaction_digest` no longer matches
  `hydra_engine.telemetry.redaction`'s current digest — the attestation
  predates the contract and should be re-run before the package is trusted

These thresholds are `TEAM_TUNABLE_POLICY` in
`engine/src/hydra_engine/thresholds.py`. Only `open` packages exert drain
pressure, the same way only `proposed` candidates do — a terminal status
already answered the question a note would raise.

## Command Surface

- `hydra.py telemetry gate` — the release gate; unchanged.
- `hydra.py telemetry report [--json]` — derived aggregates over the private
  corpus, without hand-reading `.hydra-framework.local/telemetry/events.jsonl`.
- `hydra.py telemetry evidence create --slug <s> --question "<q>"` — mints a
  package directory, envelope, `metrics.json`, and `gate-attestation.json`
  from a real gate run. Refuses when the gate verdict is `fail`. Leaves
  `## Question` / `## Findings` / `## Method` as `TODO` for a human or agent
  to fill in.
- `hydra.py validate` runs the registered `telemetry-evidence` check
  tree-wide; there is no separate `telemetry evidence validate` command.

## Capture And Absorb

Two skills, not one, mirroring the reflection queue. `telemetry evidence
create` files a package; `capabilities/skills/telemetry-evidence-absorb/`
reads `open` packages and, after owner approval, drains them into a terminal
outcome. There is no absorb command — absorption is a judgment call, the
same as it is for the reflection queue.
