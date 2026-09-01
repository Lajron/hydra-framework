# Extension Points

For canonical ownership and maintainer evidence, see the [Source Map](/project-wiki/hydra-framework/reference/source-map.md#maintainer-evidence).

Hydra's supported engine extension points are explicit, reviewable registries.
They are registered in code rather than discovered by scanning the repository at
import time. A maintainer extending one of these boundaries edits its owning
registry and keeps the matching tests current.

| Extension point | Registry location | What it owns |
| --- | --- | --- |
| Object families | `identity/object_families.py` | The families, ID prefixes, and `kind` values the resolver recognizes. |
| Object document forms | `objects/object_handlers.py` | Markdown, YAML, and Python envelope discovery. |
| Validators | `checks/validator_registry.py` | The locked `validate` and `doctor` check order. |
| Providers | `providers/capabilities.py` | Provider slugs, generated targets, and agent-wrapper renderers. |
| Command handlers | `cli/dispatch.py` | The registered command modules consumed by the parser. |
| Command-output reducers | `command_output/registry.py` | Reviewed reducers selected for recognized shell-command output. |
| Context and route providers | `knowledge/context_providers.py` | One context provider per registered object family for `compile-context` candidates. |

The registry is the documented extension location for each boundary. The
architecture keeps these registrations explicit and reviewable; it does not
promise a plugin mechanism that avoids touching the engine source.

Command-output reducers are an explicit extension point. The reducer registry
selects a reviewed reducer for recognized shell commands and falls back to an
unknown reduction when no reducer matches. Command functions still return a
`CommandResult` directly; that separate command-result type is not the reducer
registry.

The registry invariants are covered by the corresponding unit tests:
object families,
object handlers,
validators,
providers,
command registration,
command-output reducers,
and context providers.

For the exact edit sequence and validation gate for each boundary, use [Safe
Extension Recipes](/project-wiki/hydra-framework/extending-hydra/extension-recipes.md). These are source-level extension
points, not a plugin or ABI compatibility contract.
