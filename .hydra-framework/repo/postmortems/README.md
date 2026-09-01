# Postmortems

Backward-looking, incident-scoped records: what happened, its impact, why,
and what changed as a result. See `.hydra-framework/core/placement-rules.md`'s
"Runbooks And Postmortems" section for how a postmortem differs from a
flat knowledge file or a runbook.

Not a queue. Nothing here drains or gets deleted -- a postmortem is meant to
persist as the durable record of an incident. `core/placement-rules.md`'s
three-test discriminator for a shared *queue* does not apply here, because
this is not a queue.

There is no `hydra.py validate` check for postmortems yet. This README states
the expected shape as prose guidance until a real postmortem exists to design
an enforced contract against.

## Filing One

Path: `repo/postmortems/<YYYY-MM-DD>-<short-slug>.md`, dated to when the
incident was resolved or the postmortem was written, not when the incident
started.

Suggested header fields and sections:

```markdown
Status: filed
Author: <owner-slug>
Created: <YYYY-MM-DD>
Impact: <what broke, for whom, for how long>

## Timeline

<What happened, in order, with dates/times where known.>

## Root Cause

<Why it happened. Distinguish the proximate trigger from the underlying
condition that let it happen.>

## Follow-Up

<What changed as a result -- link the knowledge update or runbook
this postmortem produced, if any. "Nothing changed, this was a one-off" is a
valid answer, stated explicitly rather than left silent.>
```

## After Filing

A postmortem's narrative (Timeline, Root Cause) is not rewritten once filed,
even as later understanding improves -- only factual corrections, never
reinterpretation. If later work changes the conclusion, file a new postmortem
or an update that supersedes the earlier read, and link back to this one;
do not silently edit history to look more prescient than it was.
