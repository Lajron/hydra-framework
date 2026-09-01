# Operations

For canonical ownership and maintainer evidence, see the [Source Map](/project-wiki/hydra-framework/reference/source-map.md#maintainer-evidence).

Status: orientation

Operations is the operator route for proving that a Hydra repository is
healthy and narrowing a failure to the owning surface. Start with
[Validation](/project-wiki/hydra-framework/operations/validation.md) to choose the gate. Use
[Troubleshooting](/project-wiki/hydra-framework/operations/troubleshooting.md) for bounded diagnostic starting points,
or [Evidence and Telemetry](/project-wiki/hydra-framework/operations/evidence-and-telemetry.md) to understand what can
be retained for review and what remains local or deferred.

For exact command forms, use the [Command Surface](/project-wiki/hydra-framework/reference/command-surface.md).

## Operator Route

1. If the change is a wiki move or link edit, run the focused wiki gate.
2. If shared Hydra state changed, run the full validation gate.
3. If the failure names a package, provider surface, or engine behavior, run
   the corresponding focused check from [Troubleshooting](/project-wiki/hydra-framework/operations/troubleshooting.md).
4. Preserve the command, exit result, and finding path as review evidence.
5. Use [Evidence and Telemetry](/project-wiki/hydra-framework/operations/evidence-and-telemetry.md) when the evidence
   concerns measurements, redaction, or a future capture integration.
