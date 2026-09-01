
# Intake

Intake is Hydra's source-to-canonical pipeline.

Use this area when useful material exists but is not ready to become durable repository knowledge.

The normal lifecycle is:

`source -> raw -> extracted -> triage -> promoted -> canonical-or-archived`

Processing happens privately; only the outcome is shared. The placement rules set this
boundary.

## Folder Roles

Private, in `.hydra-framework.local/intake/`:

- `raw/`: source descriptors or safe source copies awaiting processing.
- `extracted/`: generated extraction artifacts that are useful for search and review but not canonical.
- `triage/`: cleaned staging notes that decide what is useful, duplicated, unclear, unsafe, or promotable.

Shared, here:

- `promoted/`: records linking source material to the canonical files it changed.
- `migrations/`: per-effort workspaces for clearing a whole source area, where per-item intake cannot say what is left. Shared because the end state is a property of the repository, not of a person.
- `templates/`: the formats for all of the above.

## Rules

- Do not store raw conversations as permanent memory.
- Do not commit credentials, private machine paths, secrets, or unsafe raw material.
- Keep source material in `.hydra-framework.local/intake/` and promote only sanitized durable meaning.
- Do not treat extracted or triage material as canonical.
- **A promotion record must not link to `.hydra-framework.local/`.** The author can follow that path and no teammate can, and the reader cannot tell the difference. Copy the origin, date checked, privacy note, and the claim into the record itself. `hydra.py validate` enforces this.
- Prefer linking to external systems when they are the source of truth.
- Promote only verified, useful, durable meaning into the owning canonical area.
- Archive or supersede intake material when it is stale, wrong, duplicated, or replaced.
- When clearing a source area rather than processing one source, use `migrations/` and follow `capabilities/workflows/material-migration.md`. Move originals to private staging before promoting anything.

## Promotion Targets

- `repo/knowledge/`: verified repository facts, conventions, procedures, architecture, domain knowledge.
- `core/`: durable framework rules and placement policy.
- `capabilities/`: reusable agents, skills, workflows, tools, plugins, and packs.
- `evolution/candidates/`: framework improvement proposals.
