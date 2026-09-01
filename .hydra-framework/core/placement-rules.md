# Placement Rules

Use these rules before adding or moving framework artifacts.

## Source of Truth

- If Git already owns the state, query Git instead of copying it.
- If an external system owns the state, link or reference it instead of mirroring it.
- If the framework adds durable meaning not present elsewhere, store that meaning here.

## The Three Tiers

State belongs to exactly one of three tiers. Decide by asking the tier's
question, in order.

| Tier | Question | Location | Git |
| --- | --- | --- | --- |
| Shared | Does this describe the repository? | `.hydra-framework/` | tracked, review-gated |
| Personal | Is this my structured work, that someone inherits if I vanish? | `.hydra-framework/tasks/personal/<owner>/` | tracked |
| Private | Is this my thinking, which should not be permanent? | `.hydra-framework.local/` | ignored |

"Is it safe to version?" is not the test. Most scaffolding is safe to version and
still does not belong in shared state.

Provider auto-memory, a model's own persistent per-project memory kept
outside this repository by the provider itself, is not one of these three
tiers and is not something Hydra manages. Treat it as non-authoritative until
a durable claim is promoted into shared or personal state. See
`repo/knowledge/state-tiers.md`.

### Shared

Framework rules, canonical repository knowledge, capabilities, adapters,
validation, templates, promotion records, migration ledgers, and evolution
candidates.

### Personal

Task records and their checkpoints, under your own owner directory. These are
tracked so they survive a lost machine, follow you between machines, and can be
picked up by whoever inherits the work.

They stay small because completion removes them: Git history is the archive, and
duplicating state Git owns is exactly what the rule above forbids.

Read anyone's record. Edit only your own; to take one over, use
`hydra.py task handoff`. See `repo/knowledge/offboarding-and-reaping.md` for
when and how to take over a record whose owner has gone stale or left. Hydra
does not keep an owner roster; use repository identity and the handoff/reaping
process.

### Private

Planning, open questions, half-formed decisions, review reactions, source
material, extraction artifacts, triage judgments, experiments, credentials,
machine paths, and scratch of every kind.

Private state is untracked on purpose, and not only for secrecy. People record
what is actually wrong with something only when it is not permanently attributed
in a shared repository, and a half-thought that becomes permanent becomes a fact
some later agent trusts.

`hydra.py note "<title>"` creates a dated titled note file under
`.hydra-framework.local/notes/`, such as `YYYY-MM-DD-title.md`. Stdin-only input
with no title appends to today's scratch note. Notes have no template, no
required fields, and are never validated. Capture must cost almost nothing or it
does not happen.

### The Boundary Rule

**A shared file may never cite a private file.** Whoever wrote it can follow the
link; nobody else can, and the reader cannot tell the difference between a real
citation and one they simply lack.

When promoting, inline what the shared file needs: origin, date checked, and
the claim itself, rather than pointing at the private material it came from.
`hydra.py validate` enforces this.

Ambiguous information stays private until deliberately promoted.

The narrow exception is a personal task record naming concrete private local
state in a resumability field: `Required dependencies, services, generated
artifacts, or private local requirements`, `Running state`, or `Resume check`.
Those fields may point at `.hydra-framework.local/...` files when another agent
on the same machine needs them to continue. That path is an operational
requirement, not shared evidence; shared knowledge and canonical rules must still
inline any verified claim rather than citing the private file.

## Canonical or Derived

Store verified repository facts, conventions, and procedures in `repo/`.

Store generated indexes, graphs, embeddings, retrieval structures, and summaries in `cognition/` only when they are rebuildable or clearly marked as derived.

Do not put irreplaceable knowledge only in `cognition/`.

## Intake, Pending, and Promotion

Intake processing happens privately; only its outcomes are shared.

Private, in `.hydra-framework.local/intake/`:

- `raw/`: source descriptors or safe source copies awaiting processing.
- `extracted/`: generated extraction artifacts such as text, links, metadata, summaries, or parsed data.
- `triage/`: reviewed staging notes deciding what is useful, duplicated, unclear, unsafe, or promotable.

Shared, in `.hydra-framework/intake/`:

- `promoted/`: promotion records linking source material to the canonical files it changed. Each must contain the durable content of its source descriptor, because the descriptor is private.
- `migrations/<date>-<slug>/`: one workspace per effort to clear a whole source area, holding scope and a single ledger. Its definition of done is a property of the repository, so it is shared even though it churns. Originals move to `.hydra-framework.local/migrations/<slug>/originals/` first; the shared workspace never holds them.

Also shared, in `.hydra-framework/evolution/reflections/`: dated, author-attributed session-observation packets. See its `README.md` for the packet contract and terminal outcomes.

Do not treat intake material as canonical memory.

Lightweight unverified observations go in `.hydra-framework.local/notes/`. A
shared queue is permitted only when it answers a question about the
repository (not a person), every item says who put it there, and there is a
terminal end state something forces items toward.
`repo/pending/` failed all three and stays removed. `evolution/reflections/`
passes them: sanitized session observations, author-attributed, drained by
anyone into a durable artifact or deletion. `evolution/candidates/` also
passes them: worked-out proposals, author-attributed,
with a closed status vocabulary and a staleness advisory forcing a decision
on anything left `proposed` too long. Unlike reflections, a candidate's
terminal state is a status value, not deletion -- it stays as the durable
record of a decision already made.

`repo/telemetry/packages/` also passes them: bounded,
author-attributed evidence packages derived from the private telemetry
corpus, each anchored by exactly one enveloped `telemetry-evidence` object.
Like candidates, a terminal package (`absorbed`, `superseded`, `rejected`)
stays as the durable record of a measurement already made; only `open`
packages drain. See `repo/telemetry/README.md` for the package contract.

Promote only durable meaning into its canonical owner: `repo/knowledge/`,
`capabilities/`, `core/`, `validation/`, `evolution/`, or executable engine code.

If source material is private, credential-bearing, machine-specific, or unsafe to share, keep it in `.hydra-framework.local/` and store only a sanitized source descriptor or derived conclusion in shared state.

Do not commit previously-ignored source material to shared state in order to create an archive. Private staging is the archive. Before draining a source area, verify who owns its history: if Git does not track it, the working copy is the only copy and moving it to private staging is the only undo.

## Tasks

Create a formal task record only when persistence matters: non-trivial work, blockers, interruption, handoff, multi-session effort, or team visibility.

Do not make every prompt a task.

Records live in `tasks/personal/<owner>/` and are removed on completion. `hydra.py board` shows what everyone has in flight, computed from the records themselves.

## Agents, Skills, Workflows

- Agents own roles and decision-making.
- Skills own reusable procedures or expertise.
- Workflows own repeatable coordination patterns.
- Tools own capability definitions and implementation requirements.

Before writing or editing a skill, agent, or core runtime file, follow
`core/agent-writing.md` for structure, voice, and the no-em-dash convention.

Do not duplicate skill instructions inside agent definitions. Agents should reference skills and knowledge.

## Engine Code

Hydra engine Python lives under `.hydra-framework/engine/src/hydra_engine/`.
Tests live under `.hydra-framework/engine/tests/`:

- `unit/` mirrors `src/hydra_engine/` one-to-one and is enforced by
  `hydra.py validate`.
- `repository/` holds tests that intentionally inspect this live repository.
- `contract/` holds command-output golden tests.

`.hydra-framework/scripts/hydra.py` is the stable compatibility CLI entrypoint,
not the implementation home. Keep new command behavior, validators, object
model code, provider logic, context compilation, hooks, and reusable lifecycle
logic in `hydra_engine`. Only code that must depend on the shim's own `__file__`
or preserve the hard-coded entrypoint belongs in `scripts/hydra.py`.

## Documentation Surfaces

Canonical repository knowledge lives in `repo/knowledge/`. Stable framework
rules live in `core/`; procedures live in capabilities; executable contracts
live in the engine and validation rules. Git history owns their rationale.

Human-facing docs, Obsidian notes, and wiki pages live outside `.hydra-framework/` by default, usually under `project-wiki/`. `.hydra-framework/surfaces/` documents surface contracts, ownership, sync policy, and validation expectations; it is not the place for normal teammate-facing product documentation.

Use `project-wiki/hydra-framework/` to explain how Hydra works in this repository. Use `project-wiki/<project-name>/` for human-readable product, module, feature, and system docs.

Wiki pages may be generated or drafted by AI, but durable claims must cite or link verified code, existing project docs, accepted rules, task records, or other source material. Teammates should not need to browse `.hydra-framework/` to understand product systems.

Generated documentation must identify or link its canonical source material. Do not duplicate source-of-truth state that Git, code, CI, package managers, issue trackers, or external systems already own.

## Runbooks And Postmortems

Both are Shared: they describe the repository's own operation, not a
person's in-flight work or private thinking. Neither is a
flat knowledge file, though the three are easy to conflate.

- A flat **knowledge** file (`repo/knowledge/`) is descriptive: how some
  part of the repository currently works, kept true by editing in place.
- A **runbook** is prescriptive: the concrete steps to run when a specific,
  recurring operational situation happens again -- recovering a corrupted
  object registry, restoring a task record Git can still recover, rotating a
  leaked credential. It answers "what do I actually do," not "what did we
  choose" or "how does this work." A runbook lives as a flat file directly
  under `repo/knowledge/`, named `runbook-<slug>.md`, using the same minimum
  envelope every flat knowledge file uses (`repo/knowledge/README.md`) --
  procedural knowledge is still knowledge, and reusing that envelope and its
  existing `flat-knowledge` validator is cheaper than a parallel contract for
  a directory with no content yet. Kept current by editing in place, the
  same as any other flat knowledge file; it carries no lifecycle status of
  its own beyond the envelope's `status: active`.
- A **postmortem** is backward-looking: what happened, its impact, why, and
  what changed as a result, for one specific incident. Filing one is not
  itself a choice about future behavior -- a postmortem may recommend or
  motivate a rule change, a knowledge update, or a new runbook, and should
  link to whichever it produced, but the postmortem itself just records what
  occurred. Postmortems live in `repo/postmortems/<YYYY-MM-DD>-<slug>.md`,
  one file per incident. Once filed, a postmortem's narrative is not
  rewritten to reflect hindsight -- only factual corrections, not
  reinterpretation. Postmortems are not a queue: nothing drains or deletes
  one, so this section's three-test queue discriminator does not apply to
  them. There is no engine validator for postmortems yet -- deferred, not
  built, until a real one exists to design a contract against;
  `repo/postmortems/README.md` states the expected shape (Status, Author,
  Created, Impact, Timeline, Root Cause, Follow-Up) as prose guidance in the
  meantime.
