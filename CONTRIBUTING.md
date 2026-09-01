# Contributing to Hydra

Thanks for considering a contribution. Hydra is a foundation seed, so small,
clear, well-validated changes are especially valuable.

## Before you start

For clone setup, orientation, and the first-change workflow, follow the
[New Contributor guide](project-wiki/hydra-framework/start-here/new-contributor.md).

Open an issue first when a change is substantial, changes architecture or
conventions, or would benefit from agreement before implementation. Small fixes
such as typos and broken links can be proposed directly.

## Making a change

1. Fork the repository and create a focused branch.
2. Keep the change scoped to one problem.
3. Follow the repository instructions and existing patterns.
4. Run the validation appropriate to the area you changed:
   - Wiki-only changes: `python3 .hydra-framework/scripts/hydra.py validate-wiki`
   - Changes under `.hydra-framework/`: `python3 .hydra-framework/scripts/hydra.py validate`
5. Open a pull request that explains the change and validation performed.

Do not include credentials, private notes, or machine-local state in a pull
request. Please use the [security policy](SECURITY.md) rather than a public
issue for a suspected vulnerability.

## Maintenance

This is a starter guide. Contribution, review, and release practices will be
made more specific as the project establishes them.
