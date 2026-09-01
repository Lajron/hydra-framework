# Hydra Framework

This directory is the shared, Git-tracked AI engineering layer for the repository.

It is intentionally separated from product code while remaining version controlled. The seed is small: it defines placement rules, lifecycle surfaces, task recovery, knowledge intake, repository knowledge, agents, skills, tools, documentation surfaces, and self-evolution records. Concrete behavior should evolve from real repository use.

Hydra uses this conceptual execution stack: `Coordination Graph -> Agent Loop -> Execution Harness -> Context Pack -> Prompt -> Model`. The stack explains runtime responsibilities while the repository layout remains responsibility-first.

## Operating Principles

- Ask when consequential uncertainty affects correctness.
- Do cheap read-only investigation before planning.
- Do not turn raw conversations into permanent memory.
- Store durable meaning, not duplicated external system state.
- Treat Git, issue trackers, CI, package managers, and docs platforms as sources of truth when they already own the state.
- Keep credentials, machine paths, personal preferences, and local experiments out of Git.
- Prefer concise checkpoints over noisy conversation summaries.
- Make self-modifications explainable and attributable.

## For Agents

For runtime instructions, read [`../AI_SYSTEM.md`](../AI_SYSTEM.md). Read the
rest of this README to see what lives where.

## If Hydra Was Just Copied Here

Run `python3 scripts/hydra.py adopt` for a machine-checked integration report,
then use the `adoption` skill. Do not hand-inspect the tree first, and do not
recreate framework files that a partial copy left missing.

## Common Commands

```bash
python3 .hydra-framework/scripts/hydra.py doctor                  # health check
python3 .hydra-framework/scripts/hydra.py board                   # who is working on what
python3 .hydra-framework/scripts/hydra.py note "..."              # private scratch, no ceremony
python3 .hydra-framework/scripts/hydra.py migrate-state           # move state into the 0007 tiers
python3 .hydra-framework/scripts/hydra.py export-adapters         # regenerate provider surfaces
python3 .hydra-framework/scripts/hydra.py reclaim                 # find provider files Hydra does not own
python3 .hydra-framework/scripts/hydra.py adopt                   # integration report for this repository
python3 .hydra-framework/scripts/hydra.py diff-base --base <path> # compare against the base seed
python3 .hydra-framework/scripts/hydra.py selftest                # run bundled engine tests
```

`scripts/README.md` has the full surface.

## Provider Surfaces Are Generated

`.claude/`, `.agents/`, and `.codex/` are outputs of `export-adapters`, not places
to author. Add skills and subagents under `capabilities/`, then export. If a
provider-native file already exists in one of those directories, `reclaim` will
find it and plan its promotion — that situation is expected, not misuse.

## State Tiers

Shared state describes the repository. Personal state (`tasks/personal/<owner>/`)
is one engineer's in-flight work, tracked so it survives and can be inherited.
Private state (`.hydra-framework.local/`) is thinking that should not become
permanent, and is never committed.

`core/placement-rules.md` defines the boundaries;
`repo/knowledge/state-tiers.md` is the practical guide.

## Main Areas

- `core/`: stable framework principles, architecture, lifecycle, and placement rules.
- `intake/`: promotion records and migration ledgers. Raw inputs, extraction artifacts, and triage notes are private, in `.hydra-framework.local/intake/`.
- `repo/`: repository-specific canonical knowledge and conventions.
- `tasks/`: task-record definition, plus each engineer's in-flight work under `tasks/personal/<owner>/`. Finished records are deleted; Git history is the archive.
- `capabilities/`: agents, skills, workflows, and tool capabilities. Canonical sources for every generated provider surface.
- `surfaces/`: contracts and metadata for human documentation surfaces; human-readable pages live outside `.hydra-framework/` by default, usually under `project-wiki/`.
- `cognition/`: generated or rebuildable indexes and retrieval structures.
- `engine/`: Hydra's Python engine package and bundled tests.
- `adapters/`: provider, lifecycle, and runtime integration boundaries.
- `evolution/`: evidence for framework improvements and experiments.
- `validation/`: checks that keep framework structure and knowledge coherent.
- `scripts/`: executable helpers for setup, maintenance, and migration.

## Private Layer

Use `.hydra-framework.local/` for developer-private and machine-private state.
That directory is ignored by Git. Run `hydra.py init-local` to seed it, and see
`repo/knowledge/state-tiers.md` for the intended shape.
