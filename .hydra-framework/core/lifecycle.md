# Lifecycle

Hydra's lifecycle is the default Agent Loop inside the agentic execution stack.

The Execution Harness supports this loop through instructions, tools, environment, state, and feedback. It selects context, checks readiness, preserves task state, handles blockers, and records validation evidence without storing raw conversation memory.

The normal flow is:

understand -> resolve uncertainty -> check readiness -> plan -> developer approval -> execute -> verify -> learn

## Before Non-Trivial Modification

1. Inspect cheap repository context.
2. Identify branch or worktree risk when Git exists.
3. Check active task state.
4. Record readiness for persisted non-trivial tasks.
5. Ask the first consequential blocking question if needed.
6. Produce a scoped plan for approval unless the developer has already asked for direct execution.

## Checkpoints

Create or update a checkpoint when work pauses, context is low, a blocker appears, a model handoff is likely, or another developer needs to continue.

A checkpoint stores facts, not a conversation transcript:

- task goal
- confirmed decisions
- approved plan
- current stage
- completed work
- changed files
- validation performed
- remaining work
- blockers
- useful commands or references

## Completion

When work finishes, decide what should persist:

- canonical knowledge
- reusable procedures
- follow-up tasks
- system improvement candidates
- archived checkpoint

