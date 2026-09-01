# Telemetry Evidence Package Template

Copy this file's content into
`repo/telemetry/packages/<UniqueName>/overview.md`, where `<UniqueName>` is
`<YYYY-MM-DD>-<owner-slug>-<short-slug>` (see `repo/telemetry/README.md`).
`hydra.py telemetry evidence create --slug <s> --question "<q>"` mints this
file, `metrics.json`, and `gate-attestation.json` together from a real
`telemetry gate` run — prefer it over hand-copying this template, since it
also enforces the directory-name contract and refuses a failing gate.

Do not give this template file itself a real `hydra_id` envelope — it would
be validated as an object with placeholder values and fail, so this template
keeps its envelope in a fenced code block instead of live frontmatter.

Envelope:

```yaml
---
hydra_id: hydra://telemetry-evidence/<UniqueName>
uid: <generate with: python3 -c "import uuid; print(uuid.uuid4())">
schema_version: 3
kind: telemetry-evidence
title: <Short, Specific Title>
status: open
scope: base-seed
owners:
  individual: <owner-slug>
relations: []
# Set only once absorbed into a later re-measurement:
# superseded_by: hydra://telemetry-evidence/<newer-package>
provenance:
  sources:
    - .hydra-framework/repo/telemetry/packages/<UniqueName>/gate-attestation.json
---
```

Body:

```markdown
# <Title>

Author: <owner-slug>
Created: <YYYY-MM-DD>
Window: <span of local capture measured, e.g. "2026-08-01 to 2026-08-28">
Corpus: <event count and kinds measured, e.g. "358 events across 5 kinds">

## Question

<The one question about this repository's runtime this package answers.>

## Findings

<Derived aggregates and short explanations only — counts, ratios, rates,
field names, failure classes, short sanitized snippets. No raw event rows,
no transcript text, no file contents, no `.hydra-framework.local/` path.>

## Method

<How `metrics.json` was produced — which `telemetry report` invocation, over
what window.>

## Absorption

<TODO while `status: open`. Once absorbed, superseded, or rejected: which
knowledge file, task, or candidate the finding fed, or the one
sentence explaining why it was not actionable.>
```

`metrics.json` and `gate-attestation.json` sit beside `overview.md` in the
same directory — see `repo/telemetry/README.md` for what each may contain.
