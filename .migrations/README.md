# Migration Staging

This directory is the approved staging area for already-shared source material.
Agents inventory source roots before staging, and a human approves the exact
move before material enters this directory.

It is not only for absorbing another `.hydra-framework/`. Stage any existing AI
architecture here: old provider directories, prompt libraries, agent
definitions, workflows, memory documents, conventions, previous framework
attempts, project AI docs, or another Hydra copy.

Use one source root per staged input:

```text
.migrations/<source-slug>/
```

Run:

```bash
python3 .hydra-framework/scripts/hydra.py migration inventory
python3 .hydra-framework/scripts/hydra.py migration inventory <source-slug>
python3 .hydra-framework/scripts/hydra.py migration request-stage <source-slug> <batch> --source <root> --route shared --worker-instance <id> --capability-class <class>
python3 .hydra-framework/scripts/hydra.py migration decide <source-slug> <batch> approve
python3 .hydra-framework/scripts/hydra.py migration status <source-slug> <batch>
```

Rules:

- Put only material that was already shared or safe to track here.
- Do not move material here until the bounded staging request is approved.
- Keep private, sensitive, or never-tracked originals under
  `.hydra-framework.local/migrations/<slug>/originals/`.
- Treat staged files as source material, not canonical Hydra knowledge. Staged
  material may be the authoritative source input for its own migration effort
  until it is drained, but staging never makes it canonical.
- Draining means translating or transferring accepted material into the correct
  Hydra-owned location and object model. The ledger holds each item's current
  verdict, and the migration ends when every row is terminal.
- The approved staging transition creates the workspace and ledger under
  `.hydra-framework/intake/migrations/`; rows start as pending triage.
- Do not merge staged Hydra projects or task records into this repository
  without a separate migration or integration decision.
