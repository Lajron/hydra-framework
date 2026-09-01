---
title: Execution Harness
status: active
created: 2026-07-29
owners:
  team: hydra
certainty: reviewed-docs
provenance:
  sources:
    - AI_SYSTEM.md
    - .hydra-framework/core/architecture.md
    - .hydra-framework/repo/knowledge/high-overhead-workflows.md
---

# Execution Harness

## Purpose

Hydra's Execution Harness supplies the repeatable operating conditions that let an agent work reliably across providers.

The harness is broader than a prompt. It includes instructions, available tools, environment assumptions, recoverable state, and feedback loops.

## Subsystems

The five harness subsystems (Instructions, Tools, Environment, State, Feedback) are defined in `core/architecture.md`. This file covers how they are applied in this repository rather than restating them.

Each subsystem should be explicit enough to support continuation after interruption without preserving raw conversation history.

## Deterministic Hooks

Hooks are Execution Harness infrastructure only when they are deterministic, narrow, explainable, and easy to validate.

Appropriate hook responsibilities include:

- blocking a known unsafe or policy-violating operation
- routing a known operation to the correct tool or script
- capturing lifecycle events such as task start, validation evidence, or adapter export drift
- checking generated provider surfaces against canonical Hydra sources

Hooks must not perform broad reasoning, silently rewrite canonical state, or become provider-specific sources of truth.

Private hook trust state, credentials, and machine-specific wiring belong in `.hydra-framework.local/`.

## Validation Boundaries

Validation scripts should be plain, repeatable, and minimally dependent where practical.

Fresh validation is useful when authoring context may bias the result or when changes affect high-risk framework behavior. A fresh validator should receive scoped canonical context and the changed artifacts, not the author's raw conversation.

Validation evidence should record the command, date, and result in task state or the durable outcome file when the work is persisted.

## Workflow Escalation

High-overhead workflows are Execution Harness controls selected by concrete risk
and blast radius. The trigger matrix lives in
`repo/knowledge/high-overhead-workflows.md`.

Use the smallest control that addresses the failure mode: isolated worktrees,
isolated execution environments, browser sandboxing, multi-agent review,
validation agents, or destructive-command gates. Required controls preserve
concise evidence in task state or the durable outcome rather than raw
conversation history.

## Script Boundaries

Hydra scripts may validate structure, export adapters, migrate framework state, maintain task records, or produce derived indexes.

Do not directly reuse third-party scripts, hook implementations, MCP middleware, plugin packages, or memory servers without source-code audit. External references can inform architecture, but implementation trust requires local review.

## Token Cost Guardrails

Token efficiency is an execution behavior, not only a model or vendor choice.

Runaway agent loops should be bounded before they compound cost. When the same command, tool call, error class, or failed assumption repeats across 2-3 attempts, the harness should stop normal retry behavior, summarize verified evidence, name the unverified assumption, and either change hypothesis or escalate to a human. A retry is justified only when new evidence changes the expected outcome.

Noisy outputs should be reduced before they enter model context. Prefer the failing command, exit code, relevant error lines, and the nearest useful stack frame or test failure. Avoid full logs, repeated traces, progress output, timestamps, and unrelated warnings unless the full log is itself the evidence. Preserve commands, paths, URLs, identifiers, and error literals exactly.

Token-saving tools, gateways, context compressors, browser mapping layers, or prompt-cache optimizers should not be installed or routed into shared workflows on claims alone. Adoption requires a source-code or vendor trust review, privacy review for any data leaving the machine or provider boundary, a measured baseline, and a rollback path. Prefer deterministic local filtering before network gateways when both solve the same problem.

Monitoring should be lightweight and evidence-driven. Track available input, cached-input, output, reasoning, tool-output, retry-count, loop-halt, and cost data by task, workflow, agent, or tool class when the provider or harness exposes it. Keep personal billing data, API keys, and machine-specific telemetry outside Git in `.hydra-framework.local/`.

## Relationship To Provider Adapters

Provider-visible files are adapter surfaces over the harness. They should stay small, identify canonical Hydra sources when generated, and avoid duplicating durable framework meaning.

Adapter exporters should prefer dry-run and diff-check behavior before writing generated surfaces.
