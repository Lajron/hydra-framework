# Canonical Repository Knowledge

Store verified, durable repository knowledge here.

Do not store raw conversations. Do not duplicate Git, CI, issue tracker, or package manager state unless the framework adds durable meaning those systems do not contain.

## Flat File Envelope

Flat Markdown files directly under this directory, except this README, must
start with this minimum envelope:

```yaml
---
title: <Human Title>
status: active
owners:
  team: hydra
certainty: confirmed
provenance:
  sources:
    - <repository-relative source>
---
```

`certainty:` may be replaced by `updated: YYYY-MM-DD` or
`checked_on: YYYY-MM-DD` for pending-discovery files that do not yet make a
durable claim. Active files must include `provenance.sources`; an empty list is
allowed only when the file is self-authored policy with no narrower source.

Validation also checks two cheap, explainable integrity signals: duplicate
flat-file titles, and contradictory status/certainty pairs such as
`status: active` with `certainty: superseded`. Semantic duplicate or
contradiction detection across prose is deferred until there is a concrete
query/index design; broad text comparison is too noisy for `validate`.
