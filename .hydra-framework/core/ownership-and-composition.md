# Ownership And Composition

## Responsibility Ownership

- `core/` owns stable framework rules, principles, lifecycle, and placement policy.
- `repo/` owns canonical repository-specific facts, conventions, and procedures.
- `tasks/` owns task-record definition and, under `tasks/personal/<owner>/`, each engineer's in-flight work and its checkpoints. It owns no completion or archive state: completion removes the record, because Git already holds it.
- `capabilities/agents/` owns specialist roles and decision boundaries.
- `capabilities/skills/` owns reusable procedures and expertise.
- `capabilities/workflows/` owns repeatable coordination patterns.
- `capabilities/tools/` owns capability definitions and tool requirements.
- `capabilities/tools/` owns capability definitions and tool requirements, including external integration requirements until a real integration justifies its own module directory.
- `adapters/` owns provider, lifecycle, and runtime adaptation contracts.
- `surfaces/` owns contracts for human-facing and interface-specific documentation surfaces; default human wiki pages live outside `.hydra-framework/` under `project-wiki/`.
- `cognition/` owns derived or rebuildable retrieval structures.
- `evolution/` owns improvement evidence, experiments, and seed-candidate changes.
- `validation/` owns checks that keep the framework coherent.
- `scripts/` owns executable helper behavior.

## Execution Layers

The framework composes layers in this order:

1. common seed rules
2. repository-specific adaptations
3. technology or domain extensions
4. provider adapters
5. shared knowledge state
6. personal in-flight task state
7. private developer thinking and preferences
8. private machine capability mappings
9. runtime-generated state

Layers 1-6 live in `.hydra-framework/` and are tracked; layer 6 is scoped by owner. Layers 7-8 live in `.hydra-framework.local/` and are never tracked. Runtime artifacts should be generated into explicitly marked locations and be rebuildable where possible.

The tier boundaries are in `core/placement-rules.md`.

## Breadth-First Modules

Use repeated module shape for agents, skills, workflows, plugins, integrations, and technology packs when predictable packaging helps discovery or portability.

Repeated modules should normally contain only files that carry real meaning, such as role instructions, metadata, examples, tests, or evolution notes.

## Depth-First Knowledge

Use deeper structures for repository knowledge, task recovery, docs surfaces, cognition, and evolution when each level represents a real semantic boundary.

Deep hierarchy is useful when it improves retrieval, ownership, or lifecycle management. It should not exist only to make the tree look symmetrical.

## Override Rule

Repository-specific adaptation may extend or override common seed behavior only by adding explicit repository-owned files or metadata. Do not silently edit common seed rules when the change is only useful to one repository.

If a repository-specific change may benefit the seed, record an improvement candidate in `evolution/candidates/`.
