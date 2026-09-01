# Evidence and Telemetry

For canonical ownership and maintainer evidence, see the [Source Map](/project-wiki/hydra-framework/reference/source-map.md#maintainer-evidence).

Status: operating guide

Use this page to separate evidence that can support review from telemetry that
must remain private. It also distinguishes the implemented redaction and
evidence mechanisms from capture work that still needs real provider-traffic
validation.

## Evidence Boundary

Keep review evidence proportional and reproducible: the command, its exit
result, and its relevant output path or verdict. Validation demonstrates
deterministic contracts, while human review still evaluates scope, clarity,
and whether an asserted behavior is actually implemented. See
[Validation](/project-wiki/hydra-framework/operations/validation.md#evidence-for-review) for the normal evidence route.

Telemetry is different. Local capture belongs under the private tier. Shared
state may contain a governed telemetry evidence package with derived aggregate
metrics and a redaction-gate attestation, but never raw events, prompts,
transcript text, command output, or a private local path.

## Implemented Mechanisms

The current telemetry surface provides a field-classification and redaction
contract, local append-only capture, a gate that uses poisoned fixtures, an
aggregate report, and a governed evidence-package queue. Use these commands
when a measured question needs a shareable review artifact:

```bash
python3 .hydra-framework/scripts/hydra.py telemetry gate
python3 .hydra-framework/scripts/hydra.py telemetry report --json
python3 .hydra-framework/scripts/hydra.py telemetry evidence create --slug <slug> --question "<question>"
```

The evidence command refuses to create a package when the gate verdict fails.
It creates the package structure, but the question, findings, and method still
need a reviewed explanation. `hydra.py validate` then checks the package as
part of its normal telemetry-evidence validation.

## Deferred Provider-Traffic Capture

The redaction contract and evidence queue do not prove that every provider's
live traffic is captured. Hydra's package state records capture against real
provider traffic as deferred until a future task consumes the contract. Treat
that as a routing boundary: do not claim provider-traffic coverage from a gate
attestation, and create a scoped follow-up task when such integration is ready
to be implemented and validated.
