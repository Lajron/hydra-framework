# Private Workspace

Status: operating guide

`.hydra-framework.local/` is the ignored, machine-local workspace for
unfinished thinking, scratch work, source staging, experiments, machine
observations, local indexes, and private configuration. It is not shared
Hydra memory and is not a backup. See the [State Tiers](/project-wiki/hydra-framework/concepts/state-tiers.md)
guide for the boundary.

## The Boundary

| Tier | Use | Location |
| --- | --- | --- |
| Shared | Repository rules, canonical knowledge, capabilities, validation, and other durable team state | `.hydra-framework/` |
| Personal | Tracked, resumable work another person may inherit | `.hydra-framework/tasks/personal/<owner>/` |
| Private | Personal thinking and machine-local material that is not shared evidence | `.hydra-framework.local/` |

If a thought becomes a repository fact, reusable procedure, or team policy,
promote it to its canonical shared owner. If another person must continue
unfinished work, use a personal task record rather than leaving the needed
context only in the private workspace.

## Safe Use

Run `init-local` to prepare the local workspace and `init-local --check` to
check its ignore and directory readiness. Existing private files are not
overwritten by bootstrap. The state tiers guide
owns the seeded directory shape, while the implementation owns bootstrap
behavior.

Do not commit private material as an archive or use it as shared evidence.
Shared files must never cite a concrete `.hydra-framework.local/` path because
other readers cannot verify it. When promoting private material, inline the
durable claim and cite the shared canonical owner. The complete boundary
contract is recorded for maintainers in the [Source Map](/project-wiki/hydra-framework/reference/source-map.md#maintainer-evidence),
including the narrow operational exception for personal task-record resume
requirements.
