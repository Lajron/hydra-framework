# Agent Writing

Apply these rules when writing or editing a Hydra skill, agent, or core
runtime file: `AI_SYSTEM.md`, `AGENTS.md`, `CLAUDE.md`, `core/*.md`,
`capabilities/**/*.md`, and generated adapters. It is loaded when authoring
or editing that text, not as part of the always-loaded operating contract.

## Templates

Use the shape 19 existing skill and agent files already prove out. Do not
invent a new section scheme.

**Skills** (`skill.md`): `# <Title> Skill`, then:

- `## Capability`: one sentence, what it does.
- `## Procedure`: numbered steps.
- `## Output`: what to report back, when the skill produces something worth naming.
- `## Boundaries`: bulleted constraints, each a "do not" paired with the approved alternative.
- `## Related`: links to other canonical files, for longer skills only.

A skill whose procedure only applies under a specific condition, or that
tracks state across invocations, may add a `## Trigger`, `## Inputs`, or
`## Validation Expectations` section alongside the four above. Several
existing skills do, and that information has no home in the base template.
Add sections; do not delete the required four to make room.

**Agents** (`agent.md`): `# <Title> Agent`, then `## Purpose` (one line),
`## Responsibilities` (bullets), `## Boundaries` (short prose or bullets).
Keep agents to 17 to 24 lines; if it needs more, the extra belongs in a skill
or knowledge file the agent references.

Metadata (name, description, tools, dependencies, capability class) lives in
the sidecar `metadata.yaml`, not in the markdown body. Do not restate it.

## Voice

- Open directly with the operative content. Metadata already carries the name and description; do not open with "This skill/agent/file is...".
- Use plain, direct imperative language. Escalation markers ("CRITICAL:", "MUST", ALL CAPS) do not make current models more compliant; they cause overtriggering instead. Replace "CRITICAL: You MUST use this tool when..." with "Use this tool when...".
- Give one line of reasoning when a rule needs to generalize to a case you did not list, tied to the specific decision: "Never use ellipses; the TTS engine can't pronounce them" extends correctly to a case not on the list. A bare rule cannot. Skip the reasoning when it would just be filler.
- State what to do. When a "do not" is unavoidable, pair it with the approved alternative in the same bullet: "Do not paste conversation transcripts into the record. Preserve facts and continuation state."
- One bullet, one decision. Use a "condition: action" shape where it fits: "no argument: show the board."
- Use lists for procedure, constraints, and choices. Use prose only for reasoning that cannot be expressed as a rule.
- Link to deeper canonical material instead of restating it: "Before writing shared state, read `core/placement-rules.md`," not a re-explanation of the three tiers inline.
- No em dashes in canonical, runtime, or capability text. Use a period, comma, or parenthetical instead: not "Keep it short — nobody reads past line one" but "Keep it short. Nobody reads past line one." This is a manual convention with no validator; apply it yourself, on any file you author or edit. This guide's own bad example above shows one, to name what to avoid.

## Checklist

Before you save a skill, agent, or core runtime file:

- Right template, right sections, in order.
- No restated metadata, no "This file is..." opening.
- No escalation markers; rules stated plainly.
- Every non-obvious rule carries one line of reasoning.
- Every "do not" has its alternative in the same bullet.
- Lists for rules and steps; prose only where a list would lose the reasoning.
- Links instead of restated explanations.
- No em dashes.
