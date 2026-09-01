# Provider Adapters

Provider adapters describe how a model runtime maps onto framework capabilities.

Do not place provider-specific assumptions in `core/`.


Hydra treats provider-facing files as adapter surfaces over `.hydra-framework/`.

Examples include:

- `AGENTS.md`
- `CLAUDE.md`
- `.claude/`
- `.codex/`
- `.agents/`
- provider-specific hooks, skills, subagents, plugins, MCP configuration, and generated wrappers

These files may be generated, mirrored, or hand-written when a runtime requires a physical discovery path. They must not become canonical sources for framework meaning.

Canonical meaning lives in:

- `.hydra-framework/capabilities/skills/`
- `.hydra-framework/capabilities/agents/`
- `.hydra-framework/capabilities/workflows/`
- `.hydra-framework/capabilities/tools/`
- `.hydra-framework/tasks/`
- `.hydra-framework/repo/knowledge/`
- `.hydra-framework/core/`

Private provider configuration, credentials, local MCP auth, machine paths, and hook trust state belong in `.hydra-framework.local/` or user-local provider configuration.

## Model And Effort Mapping

Shared Hydra records should name provider-neutral capability classes and effort
budgets. Provider adapters or private local configuration map those to concrete
models, reasoning-effort settings, thinking modes, local inference profiles, and
cost limits. Keep those mappings close to the runtime that owns them so core
Hydra remains usable across providers.

