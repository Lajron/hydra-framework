# Evolution Candidates

This directory is a governed, shared, temporary review queue for proposed
changes to Hydra's own framework behavior -- the channel by which this
repository's copy tells a base seed (or a future version of itself) what to
adopt, under the placement rules. It is governed the way
`core/placement-rules.md` requires any shared, temporary, churning queue to
be: every item answers a question about the repository, says who filed it,
and has a closed status vocabulary forcing a decision on anything left
`proposed` too long.

## When Not To Use It

If the thought is a raw session observation -- friction, a repeated gap, a
piece of feedback with no worked-out answer yet -- file it in
`evolution/reflections/` instead, or privately with `hydra.py note
"<title>"` if it is not yet ready to be shared. Mixing raw observations into
this queue degrades it as seed-reconciliation input.

Use this queue once you have an actual proposal: a change, why it should
happen, and what evidence supports it.

## Packet Contract

Path: `evolution/candidates/<YYYY-MM-DD>-<short-slug>.md`, or a bare
`<short-slug>.md` for a proposal that reviews another dated candidate rather
than standing alone. Copy `evolution/templates/improvement-record.md`.

Required header fields, above the first `## ` section heading:

```markdown
Status: proposed
Author: <owner-slug>
Created: <YYYY-MM-DD>
```

`evolution/README.md` lists the body sections a complete proposal should
cover (Change, Trigger, Rationale, Evidence, Result, Scope Assessment). Those
are prose guidance, not `hydra.py validate` errors -- only the three header
fields above are mechanically enforced.

A candidate large enough to outgrow one file may split into a router file
(the original path, holding what is settled and a table of contents) plus a
same-named subdirectory of part files. Only the router file carries the
header; its subdirectory holds content the router already accounts for, not
separate queue entries, and is not scanned by `hydra.py validate`.

### Status Vocabulary

A closed set of five values:

- `proposed` -- filed, awaiting a decision. The default, and the only
  non-terminal value.
- `accepted` -- judged worth adopting, whether or not implementation has
  started.
- `rejected` -- considered and declined. Kept, not deleted, so the same idea
  is not re-proposed blind.
- `captured` -- an evidentiary or recommendation record whose content already
  served its purpose (fed an accepted candidate or a settled section of
  another candidate) without itself being a standalone
  accept/reject choice.
- `superseded` -- was `proposed` or `accepted`, no longer the live version.

`hydra.py validate` rejects any other value.

## Terminal Outcomes

Unlike `evolution/reflections/`, a terminal outcome here is a status value,
not file deletion. `accepted`, `rejected`, `captured`, and `superseded`
candidates stay in this directory permanently -- they are the durable record
of a decision this repository already made. Only `proposed` candidates are
still open work.

## Drain Expectations

`hydra.py validate` emits an advisory note, never a build failure, for a
`proposed` candidate whose `Created:` date is older than the staleness
threshold. This threshold is `STALE_PROPOSED_CANDIDATE_DAYS` in
`engine/src/hydra_engine/thresholds.py` -- `TEAM_TUNABLE_POLICY`, a team that
decides differently may set it differently. There is no queue-depth note:
candidates are meant to accumulate as terminal-status history, not drain to
zero, so an unbounded count is not itself a failure signal here the way it is
for reflections.

## Author Attribution

`Author:` names who filed the candidate, the same as `evolution/reflections/`
packets. There is no `Reviewer:` field: anyone may absorb or decide a
candidate, and who actually did, and when, is recorded by the commit that
changes its `Status:`.
