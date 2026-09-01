---
title: Silent Failure Modes
status: active
created: 2026-07-30
owners:
  team: hydra
certainty: confirmed
provenance:
  sources:
    - .hydra-framework/core/placement-rules.md
    - .hydra-framework/scripts/hydra.py
---

# Silent Failure Modes

## Purpose

Every entry here has actually produced a wrong result in this repository, and they
share one property: **they pass silent**. Nothing errors, `hydra.py validate`
reports ok, and the change looks applied. The failure surfaces later, in a
different session, usually as an agent trusting state that is not true.

Read this before changing the task contract, the module format, the adapter
exporters, or a downstream copy of Hydra.

This file is the counterpart to `complexity-review` and `minimum-correct-diff`,
which say what to look for. This says what looks clean and is not.

Each entry states the failure, why it stays silent, and how to detect it. An
entry without a detection method does not belong here.

## Contents

1. Validate checks label presence, not value correctness
2. The contract-doc cross-check accepts a passing mention
3. Module files outside `skill.md` are dropped at export
4. Non-Markdown files in a provider surface escape classification
5. Wholesale file copying clobbers a downstream lineage block
6. Byte-comparing two Hydra copies reports generated-artifact noise
7. Seed-only claims stay true in the seed and become false in every copy
8. A shared file citing a private path reads as a real citation
9. A shared directory of everyone's records still passes every check

---

## 1. Validate checks label presence, not value correctness

`validate_task_file` (`scripts/hydra.py`) tests `item not in text` against
`REQUIRED_TASK_SECTIONS`. It is a substring check over the whole file.

A task record passes validation with every required label present and every value
empty, still set to a template placeholder, or filled in with prose that does not
answer the field. `Resume check:` with nothing after it is indistinguishable from
`Resume check:` with a real command.

**Why it stays silent:** `validate` exits 0, so an agent reports the record as
verified. The field list is satisfied; the record is useless.

**Detection:** read the values, not the exit code. `task-lifecycle/skill.md` states
the rule directly — a generated record still full of template placeholders is
worse than no record. When handing off, confirm each field answers its question.

**Do not fix by tightening the substring check into value parsing.** Free-form
values are intentional. The check is a floor, not a proof.

## 2. The contract-doc cross-check accepts a passing mention

`validate_task_contract_docs` keeps `REQUIRED_TASK_SECTIONS`,
`tasks/templates/task.md`, and `capabilities/workflows/task-lifecycle.md` from
drifting. For the workflow doc it lowercases the file, strips `#` and `:` from
each required item, and checks whether that label appears anywhere in the text.

So the workflow doc satisfies the check by *mentioning* a field in passing. A
sentence like "record running state if relevant" passes identically to a full
definition of what Running state must contain.

**Why it stays silent:** the guard exists and reports ok, which reads as "the
three copies agree." It only proves the string is present in all three.

**Detection:** when adding a required field, confirm by reading that the workflow
doc *defines* the field — what goes in it, what the default is, and how it differs
from adjacent fields. The template and `REQUIRED_TASK_SECTIONS` are exact-match
and do not have this weakness; only the doc side does.

## 3. Module files outside `skill.md` are dropped at export

`build_skill_wrapper` reads exactly `metadata.yaml` and `skill.md` from a module
directory and returns exactly two files: `SKILL.md` and `.hydra-adapter.yaml`.
`build_agent_wrapper` is the same shape over `agent.md`.

Adding `references/detail.md` or `scripts/check.py` to
`capabilities/skills/<name>/` therefore produces no export, no warning, and no error.
The canonical file exists, is committed, and never reaches any provider surface.

**Why it stays silent:** the module directory looks richer, `validate` passes
because `validate_module_metadata` only requires the body file and metadata keys,
and the skill still works — just without the detail the author believed they added.

**Detection:** after adding anything to a module directory, run
`export-adapters` and confirm the file appears under `.claude/skills/<name>/`.
If a module needs supporting files, the exporters must change first.

## 4. Non-Markdown files in a provider surface escape classification

`classify_surfaces` skips any file whose suffix is not `.md` or `.toml`. A
hand-written `.claude/skills/deploy/SKILL.md` is correctly reported as `orphaned`
with the Hydra path it should become. A hand-written
`.claude/skills/deploy/run.sh` is reported as nothing at all.

**Why it stays silent:** the surface-classification guard is the mechanism that
stops provider directories becoming independent sources of truth. It covers the
document case well, which makes it easy to assume it covers everything.

**Detection:** `find .claude .agents .codex -type f ! -name '*.md' ! -name '*.toml'`
and check each hit against `SURFACE_IGNORED_NAMES` and the hand-maintained
allowlist in the provider adapter README.

## 5. Wholesale file copying clobbers a downstream lineage block

A repository that adopted Hydra carries local state inside otherwise-shared
files. `manifest.yaml` in an adopting repo gains a `lineage:` block recording
`base_seed_version`, `adopted_into`, `adopted_date`, and `divergence_policy`. The
seed itself has no such block.

Copying seed files into the downstream repo with a recursive copy silently
deletes it.

**Why it stays silent:** nothing validates lineage presence. The next
`diff-base` run then cannot separate deliberate divergence from stale drift,
which is the entire purpose of the ledger and the lineage block. The damage
appears one reconciliation later, as a decision made on bad information.

**Detection:** before copying, diff the specific files you intend to change
rather than the tree. Never copy `manifest.yaml` downstream. After any transfer,
confirm `lineage:` is still present in the downstream manifest.

## 6. Byte-comparing two Hydra copies reports generated-artifact noise

`diff -rq` between a seed and a copy reports `scripts/__pycache__/*.pyc` as
differing whenever both have been run. The `.pyc` files are gitignored
(`.gitignore` matches `__pycache__/`), so they are invisible in `git status` and
easy to forget.

**Why it stays silent:** the inverse of the usual case. Nothing is broken, but
the noise sits in the same output as real differences, and a real one-line
difference is easy to skim past in a list that includes byte-level churn nobody
cares about.

**Detection:** compare with `diff -rq --exclude=__pycache__`, or compare only
tracked files. Treat a `.pyc` line in comparison output as noise, and never as
evidence that a copy is current or stale.

## 7. Seed-only claims stay true in the seed and become false in every copy

The inverse of entry 5. There, copying deletes downstream state. Here, copying
installs an assertion that is correct in the seed and wrong everywhere else.

`evolution/adaptations.md` ends with "This repository is the base seed itself, so
it has nothing to diverge from and the ledger is expected to stay empty here."
That is true in the seed. Carried into an adopting repository verbatim, it
instructs an agent not to fill in the ledger — in precisely the repository whose
ledger is load-bearing for reconciliation.

**Why it stays silent:** the sentence is confident, canonical-looking, and lives
in the file it describes. Nothing validates a claim about repository identity
against `manifest.yaml`, so the copy contradicts its own lineage block without
either side reporting a conflict. The result is an empty ledger that reads as
"no deliberate divergence" rather than "never recorded."

**Detection:** any shared file asserting what *this* repository is must be
checked against `lineage:` in `manifest.yaml`. A repository with a lineage block
is a copy, whatever the prose says. When writing such a sentence in the seed,
phrase it conditionally — "if this repository has no `lineage:` block" — so it
stays true after copying, rather than stating it as fact about the current repo.

## 8. A shared file citing a private path reads as a real citation

The placement rules put intake `raw`, `extracted`, and `triage` in the
untracked private tier. Promotion records stay shared and cite their sources.

A promotion record whose source line reads
`.hydra-framework.local/intake/raw/<date>-<slug>-source.md` is correct for its
author and useless for everyone else. Worse, it is *indistinguishable* from a
working citation: the reader sees a specific path, assumes provenance was
recorded, and has no way to tell that the file cannot exist on their machine.

The same trap applies to any shared file — a
knowledge file pointing at a triage judgment, a task record naming a private log.

**Why it stays silent:** Markdown link validation only checks links it can
resolve as repository paths, and the author can always follow the link. Nothing
in a normal review distinguishes "the file is private" from "the file is missing
on my checkout," and both look like a citation that exists.

**Detection:** `validate_tier_boundaries` in `scripts/hydra.py` fails on any
shared Markdown file citing a concrete file inside a private *content* area —
`intake/`, `notes/`, `tasks/`, `migrations/`, `evolution/`, `scratch/`, `logs/`.

It deliberately permits three things, because describing the tier is not the
failure — depending on its contents for meaning is:

- naming a directory in prose
- `<placeholder>` paths, which name a shape rather than a file
- the conventional config locations (`monitoring/token-hooks.json`,
  `developer/preferences.md`, `machine/profile.yaml`), which have fixed names
  everyone has their own copy of. Telling a reader where to put theirs is not
  citing yours.

**Fix by inlining, not by re-sharing the source.** Copy the durable content into
the shared file: origin, date checked, licence note, and the claim. Moving the
private material back into Git to satisfy the link is the wrong repair and
usually the reason it was private.

## 9. A shared directory of everyone's records still passes every check

Before owner-scoped task records, `tasks/active/` was shared. With one person it meant "what I am
working on." With eight it means "what anyone ever started and did not clean up,"
and `hydra.py validate` reports ok either way, because each record individually
satisfies `REQUIRED_TASK_SECTIONS`.

This is the most expensive entry here, because the wrong answer is confident. An
agent asked "what is in flight?" reads the directory, gets twenty records, and
has no way to tell which are live, which were abandoned in week three, and which
belong to someone who left.

**Why it stays silent:** structural validity and semantic truth are different
properties, and only the first is checkable per file. Every record is well
formed. The directory as a whole is a lie, and no per-file check can see it.

**Detection:** ask whether a directory's *name* still describes its contents for
someone who did not create them. Owner scoping (`tasks/personal/<owner>/`) makes
the name true again by narrowing what it claims, and deleting records on
completion keeps it that way. `validate` notes records not updated in fourteen
days — that note is the closest available proxy for abandonment, and it is
advisory because the alternative is failing someone's build over bookkeeping.

**The general rule:** when shared state accumulates per-person, per-session
scaffolding, the failure is not that the files are wrong. It is that the
container's name stops being true, and nothing about a valid file can detect it.
