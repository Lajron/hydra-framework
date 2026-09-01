# Skills

Skills are reusable capabilities, procedures, or expertise that agents can invoke.

Skills may be common, technology-specific, domain-specific, repository-specific, developer-private, or machine-dependent. Shared skills belong here only when they are safe and useful to version.

Recommended skill shape:

- `skill.md`: capability and procedure.
- `metadata.yaml`: scope, dependencies, provider requirements.
- `examples/`: optional examples.

## Promotion Criteria

Promote a repeated workflow into a skill when it:

- prevents meaningful re-derivation
- has clear inputs and outputs
- has a stable procedure
- can describe validation expectations
- is cheaper to maintain than to rediscover

Skills should be atomic workflow capabilities, not broad personas.

Retire or supersede skills when they drift from repository reality or add coordination overhead without improving outcomes.

