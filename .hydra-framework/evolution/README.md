# Framework Evolution

Use this area to capture potential improvements to the framework.

`adaptations.md` is the append-only ledger for intentional divergence from a
base seed. Record repo-local adaptations and promotion candidates there with
`hydra.py evolution record`; reconciliation reads it on demand before deciding
whether a diff is stale drift or a deliberate local choice.

`candidates/` is the governed queue for worked-out proposals -- see
`candidates/README.md` for the packet contract and status vocabulary.
Improvement records should explain:

- what changed
- why it changed
- what triggered it
- whether it was helpful
- supporting evidence
- whether it is repository-specific
- whether it may be useful to the common seed architecture

`reflections/` is the governed queue for raw session observations that are
not yet a worked-out proposal -- see `reflections/README.md`.
