# Agents

Agents are specialist roles that make decisions and coordinate work.

Agents may reference skills, workflows, tools, and knowledge. They should not duplicate canonical knowledge or skill instructions.

Recommended agent shape:

- `agent.md`: role, responsibilities, boundaries, inputs, outputs.
- `metadata.yaml`: scope, maturity, dependencies, evolution notes.
- `examples/`: optional usage examples.


Hydra treats mini-agents and provider subagents as first-class Execution Harness components. Use them for focused checking, research, review, validation, summarization, or other isolated work when they reduce main-context noise or improve confidence.

Provider-specific subagent files are adapters over canonical Hydra agent definitions.
