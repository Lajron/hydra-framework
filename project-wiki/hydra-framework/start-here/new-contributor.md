# New Contributor

This is the post-clone path for a normal clone of the repository. Hydra is
already installed in this repository, so setup starts with the private local
tier and a health check.

## 1. Prepare The Clone

Run:

```bash
python3 .hydra-framework/scripts/hydra.py init-local
python3 .hydra-framework/scripts/hydra.py doctor
python3 .hydra-framework/scripts/hydra.py install-hooks  # optional
```

`init-local` creates missing machine-private state under
`.hydra-framework.local/`. `doctor` checks the clone's required paths, owner,
private tier, cache lifecycle, and generated provider surfaces. The hooks are
optional per-clone convenience tooling.

This is different from copying Hydra into another repository. Use the
[new-repository adoption route](/project-wiki/hydra-framework/start-here/adopt-a-repository.md) for that path.

## 2. Orient Before The First Change

Read the [Hydra Framework orientation](/project-wiki/hydra-framework/hydra-framework.md), then run:

```bash
python3 .hydra-framework/scripts/hydra.py board
```

The board shows active work and ownership. For the practical first-work
checklist, use [Working With Hydra](/project-wiki/hydra-framework/working-with-hydra/working-with-hydra.md)
and its [First Task Walkthrough](/project-wiki/hydra-framework/working-with-hydra/first-task.md).

## 3. Make And Check A Change

Read only the canonical material relevant to the task. Use a task record when
work is non-trivial, spans sessions, needs handoff, or should remain visible
to the team. Keep private planning in `.hydra-framework.local/`.

Before review, validate the surface you changed. Wiki-only work uses
`validate-wiki`; changes under `.hydra-framework/` also use `validate`. The
[Common Questions](/project-wiki/hydra-framework/start-here/common-questions.md) page routes the detailed procedures.

## Maintainer Route

The setup, boundary, and audience owners are collected in the
[Source Map](/project-wiki/hydra-framework/reference/source-map.md#maintainer-evidence).
