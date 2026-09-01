# Model Neutrality

The framework depends on capabilities, not provider identity.

Relevant capabilities may include:

- reasoning quality
- effort budget or reasoning depth
- context capacity
- tool access
- code editing
- structured output
- privacy properties
- speed
- cost
- subagent support

Provider-specific behavior belongs in `adapters/providers/` or private local configuration. Shared core rules must remain usable by Claude, Codex, local models, and future providers.

## Effort Budget

Hydra names model effort as a provider-neutral budget, not as a vendor setting.
Use the smallest budget that can satisfy the task after scoped context loading:

- `minimal`: deterministic formatting, classification, routing, or log triage
- `low`: narrow local edits or summaries with direct validation
- `standard`: normal implementation, review, or documentation tasks
- `high`: architecture, migration, security, cross-module contracts, or unclear requirements
- `max`: rare use for high-risk work where cheaper routes already lack enough reasoning depth

Provider adapters or private local runtime config map these budgets to concrete
model parameters such as reasoning effort, thinking mode, model family, or local
inference profile.

