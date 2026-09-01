# Task State

Task records capture work whose loss would cost the next agent real effort:
non-trivial, interrupted, blocked, multi-session, handed off, or worth the team
seeing.

Do not make every prompt a task.

## Directories

- `personal/<owner>/`: your active task records, and `checkpoints/` beneath them.
- `templates/`: task and checkpoint formats.

There is no `active/`, `completed/`, or `archive/`. Records are per-owner while
in flight, and removed when finished — Git history is the archive. The placement rules
explains why.

## Ownership

Your owner slug resolves from `--owner`, then `HYDRA_OWNER`, then
`git config user.email`, slugified as the full resolved candidate. If that
candidate is an email address, the domain is kept:
`dana.reed@example.com` becomes `dana-reed-example-com`. If none
is set, commands fail rather than guessing which directory to write to.

Read anyone's record. Edit only your own. Use `hydra.py task handoff` to take one
over, so the record and its owner never disagree.

## Commands

| Need | Command |
| --- | --- |
| See what everyone has in flight | `hydra.py board` |
| See only yours | `hydra.py board --owner <you>` |
| Start a record | `hydra.py task start <name> --goal "..."` |
| Checkpoint before a pause | `hydra.py task checkpoint <record>` |
| Hand it to someone | `hydra.py task handoff <record> --to <owner>` |
| Finish it | `hydra.py task complete <record> --outcome <path\|none>` |
| Find a finished one | `git log --diff-filter=D -- <path>` |

`--outcome` must name a file that exists, or the literal `none`. It asks the only
question that matters at completion: where did the durable meaning go? The record
is scaffolding; the knowledge file it produced is the artifact.

One authoritative record per piece of work. Do not create competing records for
the same objective.

Private thinking does not belong in a record. It goes in
`.hydra-framework.local/` — see `hydra.py note`.
