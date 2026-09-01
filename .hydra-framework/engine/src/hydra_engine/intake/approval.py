"""Approval-aware orchestration for bounded migration batches.

The module deliberately owns only the small durable state machine.  Agents may
prepare requests, proposals, and validation evidence, but source moves,
canonical writes, and staged-original removal happen only while applying an
approved gate.
"""

from __future__ import annotations

from hydra_engine.documents.tokens import display_path, is_relative_to, write_text
from hydra_engine.intake import approval_actions as actions
from hydra_engine.intake import approval_state as state_support
from hydra_engine.intake.paths import IntakePaths
from hydra_engine.intake.staging import validate_migration_slug
from hydra_engine.ports import clock as clock_port


def request_staging(
    paths: IntakePaths,
    slug: str,
    batch: str,
    sources: list[dict],
    *,
    drafting_chain: list[object],
    capability_class: str,
) -> dict:
    """Inventory exact source roots and request the batch's staging gate."""
    slug, batch = state_support.slugs(slug, batch)
    state_support.validate_capability_class(capability_class)
    chain = state_support.validate_drafting_chain(drafting_chain, default_capability_class=capability_class)
    existing = state_support.load_optional(paths, slug, batch)
    if existing and existing["phase"] != "staging-revision-required":
        raise FileExistsError(f"migration batch already exists: {batch}")

    items = actions.inventory_sources(paths, slug, sources)
    if not items:
        raise ValueError("staging request must contain at least one source root")
    reasons = ["staging-move"]
    classifications = {tag for item in items for tag in item["classifications"]}
    if classifications & state_support.RISK_CLASSIFICATIONS:
        reasons.append("sensitive-or-private-material")
    if any(item["route"] == "private" for item in items):
        reasons.append("sensitive-or-private-material")
    if classifications & state_support.AMBIGUOUS_CLASSIFICATIONS:
        reasons.append("ambiguous-classification")
    if any(item["git"]["status"] in {"unknown", "mixed"} for item in items):
        reasons.append("ambiguous-git-status")

    revision = existing["revision"] if existing else 0
    state = {
        "schema": state_support.APPROVAL_SCHEMA,
        "slug": slug,
        "batch": batch,
        "workspace": display_path(state_support.workspace(paths, slug, batch, existing=existing), paths.root),
        "revision": revision,
        "phase": "awaiting-staging-approval",
        "capability_class": capability_class,
        "drafting_chain": chain,
        "source_items": items,
        "proposal": None,
        "validation": None,
        "reconciliation": None,
        "used_validator_instances": list(existing.get("used_validator_instances", [])) if existing else [],
        "current_approval": state_support.gate(
            "staging",
            revision,
            reasons,
            {
                "moves": [
                    {
                        "source_path": item["source_path"],
                        "source_digest": item["source_digest"],
                        "destination_path": item["planned_staged_path"],
                        "route": item["route"],
                        "git": item["git"],
                    }
                    for item in items
                ]
            },
        ),
        "history": list(existing.get("history", [])) if existing else [],
    }
    state_support.save(paths, state)
    return state


def load_batch(paths: IntakePaths, slug: str, batch: str) -> dict:
    """Load one dated batch state without changing it."""
    return state_support.load_batch(paths, slug, batch)


def batch_status(paths: IntakePaths, slug: str, batch: str) -> dict:
    """Compatibility-friendly read-only name for :func:`load_batch`."""
    return load_batch(paths, slug, batch)


def submit_proposal(paths: IntakePaths, slug: str, batch: str, proposal: dict) -> dict:
    """Bind a package/unit proposal to its drafts and current targets."""
    state = load_batch(paths, slug, batch)
    if state["phase"] not in {"staged", "publication-revision-required"}:
        raise ValueError(f"cannot submit a proposal while batch phase is `{state['phase']}`")
    state_support.reject_provider_specific_keys(proposal)
    package_slug = validate_migration_slug(str(proposal.get("package_slug", "")))
    package_root = paths.hydra / "repo/knowledge/knowledge-packages" / package_slug
    batch_root = state_support.batch_root(paths, state)
    drafts_root = batch_root / "drafts"
    raw_units = proposal.get("units")
    if not isinstance(raw_units, list) or not raw_units:
        raise ValueError("proposal units must be a non-empty list")

    units: list[dict] = []
    targets: set[str] = set()
    reasons = ["canonical-publication"]
    if not package_root.exists():
        reasons.append("new-package-boundary")
    for raw in raw_units:
        if not isinstance(raw, dict):
            raise ValueError("each proposal unit must be an object")
        draft = state_support.contained_relative(paths.root, str(raw.get("draft_path", "")), "draft path")
        if not is_relative_to(draft, drafts_root) or not draft.is_file():
            raise ValueError("proposal draft_path must name an existing file below the batch drafts directory")
        target = state_support.contained_relative(paths.root, str(raw.get("target_path", "")), "target path")
        if not is_relative_to(target, package_root) or target == package_root:
            raise ValueError(f"proposal targets must stay within package `{package_slug}`")
        target_rel = display_path(target, paths.root)
        if target_rel in targets:
            raise ValueError(f"duplicate proposal target: {target_rel}")
        targets.add(target_rel)
        if target.exists():
            reasons.append("target-conflict")
        source_items = raw.get("source_items", [])
        if not isinstance(source_items, list) or any(not isinstance(item, str) for item in source_items):
            raise ValueError("unit source_items must be a list of source item paths")
        known_items = {finding["path"] for item in state["source_items"] for finding in item["findings"]}
        unknown = sorted(set(source_items) - known_items)
        if unknown:
            raise ValueError(f"proposal names unknown source items: {', '.join(unknown)}")
        units.append(
            {
                "draft_path": display_path(draft, paths.root),
                "draft_digest": state_support.path_digest(draft),
                "target_path": target_rel,
                "target_digest": state_support.path_digest(target) if target.exists() else None,
                "source_items": sorted(set(source_items)),
            }
        )

    proposal_chain = proposal.get("drafting_chain", state["drafting_chain"])
    proposal_chain = state_support.validate_drafting_chain(proposal_chain)
    normalized = {
        "package_slug": package_slug,
        "revision": state["revision"],
        "drafting_chain": proposal_chain,
        "units": units,
    }
    normalized["proposal_digest"] = state_support.json_digest(normalized)
    write_text(batch_root / "proposal.json", state_support.json_text(normalized))
    state["proposal"] = normalized
    state["drafting_chain"] = proposal_chain
    state["validation"] = None
    state["current_approval"] = None
    state["phase"] = "awaiting-independent-validation"
    state_support.save(paths, state)
    return state


def record_validation(paths: IntakePaths, slug: str, batch: str, evidence: dict) -> dict:
    """Record a fresh independent validation and open publication approval."""
    state = load_batch(paths, slug, batch)
    if state["phase"] != "awaiting-independent-validation" or not state["proposal"]:
        raise ValueError(f"cannot validate while batch phase is `{state['phase']}`")
    state_support.reject_provider_specific_keys(evidence)
    validator = str(evidence.get("validator_instance", "")).strip()
    if not validator:
        raise ValueError("validator_instance is required")
    drafting_instances = {entry["instance"] for entry in state["drafting_chain"]}
    if validator in drafting_instances:
        raise ValueError("validator instance must differ from every drafting-chain instance")
    if validator in state.get("used_validator_instances", []):
        raise ValueError("validator instance must be fresh for every canonical proposal")
    state_support.validate_capability_class(str(evidence.get("capability_class", "")))
    if evidence.get("fresh_instance") is not True or evidence.get("no_drafting_context") is not True:
        raise ValueError("validator must attest a fresh instance with no drafting-chain context")
    if evidence.get("proposal_digest") != state["proposal"]["proposal_digest"]:
        raise ValueError("validation proposal digest does not match the current proposal")
    if "drafting_chain" in evidence and evidence["drafting_chain"] != state["drafting_chain"]:
        raise ValueError("validation drafting_chain does not match the proposal drafting chain")
    checks = evidence.get("checks")
    if not isinstance(checks, list) or not checks:
        raise ValueError("validation checks must be a non-empty list")
    if any(not isinstance(check, dict) or check.get("exit_code") != 0 for check in checks):
        raise ValueError("every validation check must report exit_code 0")
    commands = {str(check.get("command", "")) for check in checks}
    if not any("validate-package-docs" in command for command in commands):
        raise ValueError("validation evidence requires validate-package-docs")
    if not any(_has_command_words(command, "ref", "check") for command in commands):
        raise ValueError("validation evidence requires `hydra.py ref check`")

    target_digests = evidence.get("target_digests")
    expected_targets = {unit["target_path"]: unit["target_digest"] for unit in state["proposal"]["units"]}
    if target_digests != expected_targets:
        raise ValueError("validation target digests do not match the proposal")
    validation = {
        "validator_instance": validator,
        "capability_class": evidence["capability_class"],
        "fresh_instance": True,
        "no_drafting_context": True,
        "proposal_digest": evidence["proposal_digest"],
        "target_digests": target_digests,
        "checks": checks,
    }
    state["validation"] = validation
    state.setdefault("used_validator_instances", []).append(validator)
    reasons = ["canonical-publication"]
    package_root = paths.hydra / "repo/knowledge/knowledge-packages" / state["proposal"]["package_slug"]
    if not package_root.exists():
        reasons.append("new-package-boundary")
    if any(unit["target_digest"] is not None for unit in state["proposal"]["units"]):
        reasons.append("target-conflict")
    state["current_approval"] = state_support.gate(
        "publication",
        state["revision"],
        reasons,
        {
            "proposal_digest": state["proposal"]["proposal_digest"],
            "units": [
                {
                    "draft_path": unit["draft_path"],
                    "draft_digest": unit["draft_digest"],
                    "target_path": unit["target_path"],
                    "target_digest": unit["target_digest"],
                }
                for unit in state["proposal"]["units"]
            ],
        },
    )
    state["phase"] = "awaiting-publication-approval"
    state_support.save(paths, state)
    return state


def request_closure(paths: IntakePaths, slug: str, batch: str, reconciliation: object) -> dict:
    """Require a terminal ledger status for every staged source item."""
    state = load_batch(paths, slug, batch)
    if state["phase"] not in {"published", "closure-revision-required"}:
        raise ValueError(f"cannot request closure while batch phase is `{state['phase']}`")
    rows = state_support.normalize_reconciliation(reconciliation)
    expected = {finding["path"] for item in state["source_items"] for finding in item["findings"]}
    actual = set(rows)
    missing = sorted(expected - actual)
    extra = sorted(actual - expected)
    if missing or extra:
        details = []
        if missing:
            details.append(f"unreconciled: {', '.join(missing)}")
        if extra:
            details.append(f"unknown: {', '.join(extra)}")
        raise ValueError("closure reconciliation does not cover every source item (" + "; ".join(details) + ")")
    invalid = sorted({status for status in rows.values() if status not in state_support.TERMINAL_LEDGER_STATUSES})
    if invalid:
        raise ValueError(f"closure requires terminal statuses; invalid: {', '.join(invalid)}")

    removal_paths = []
    for item in state["source_items"]:
        staged = state_support.contained_relative(paths.root, item["staged_path"], "staged removal path")
        state_support.assert_expected_staging_path(paths, state["slug"], item["route"], staged)
        removal_paths.append({"path": item["staged_path"], "digest": state_support.path_digest(staged)})
    state["reconciliation"] = {
        "items": [{"path": path, "status": rows[path]} for path in sorted(rows)],
        "removal_paths": removal_paths,
    }
    state["current_approval"] = state_support.gate(
        "closure",
        state["revision"],
        ["final-staged-original-removal"],
        {"removal_paths": removal_paths},
    )
    state["phase"] = "awaiting-closure-approval"
    state_support.save(paths, state)
    return state


def decide(
    paths: IntakePaths,
    slug: str,
    batch: str,
    outcome: str,
    *,
    rationale: str = "",
    guidance: str = "",
    actor: str = "",
) -> dict:
    """Record and, for approval, immediately apply the current bounded gate."""
    state = load_batch(paths, slug, batch)
    if outcome not in state_support.OUTCOMES:
        raise ValueError(f"approval outcome must be one of: {', '.join(sorted(state_support.OUTCOMES))}")
    gate = state.get("current_approval")
    if not gate or gate.get("status") != "pending":
        raise ValueError("batch has no pending approval")
    if outcome == "reject" and not rationale.strip():
        raise ValueError("reject requires a terminal rationale")
    if outcome == "revise" and not guidance.strip():
        raise ValueError("revise requires guidance")

    decision = {
        "gate": gate["kind"],
        "outcome": outcome,
        "revision": state["revision"],
        "actor": actor,
        "rationale": rationale,
        "guidance": guidance,
        "decided_at": clock_port.now_utc_iso(),
    }
    state["history"].append(decision)
    gate["status"] = outcome
    gate["decision"] = decision
    if outcome == "reject":
        state["phase"] = "rejected"
        state_support.save(paths, state)
        return state
    if outcome == "revise":
        state["revision"] += 1
        state["phase"] = f"{gate['kind']}-revision-required"
        state["current_approval"] = None
        if gate["kind"] == "publication":
            state["validation"] = None
        elif gate["kind"] == "closure":
            state["reconciliation"] = None
        state_support.save(paths, state)
        return state

    if gate["kind"] == "staging":
        actions.apply_staging(paths, state)
    elif gate["kind"] == "publication":
        actions.apply_publication(paths, state)
    elif gate["kind"] == "closure":
        actions.apply_closure(paths, state)
    else:
        raise ValueError(f"unknown approval gate: {gate['kind']}")
    gate["status"] = "approved"
    state_support.save(paths, state)
    return state


def _has_command_words(command: str, first: str, second: str) -> bool:
    words = command.split()
    return any(left == first and right == second for left, right in zip(words, words[1:]))
