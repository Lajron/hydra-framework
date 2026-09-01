"""Shared Hydra configuration loading and validation."""

from __future__ import annotations

import dataclasses
from pathlib import Path

from hydra_engine.documents.frontmatter_blocks import parse_yaml, yaml_list, yaml_map, yaml_str
from hydra_engine.documents.tokens import HydraYamlError, display_path
from hydra_engine.finding import Finding
from hydra_engine import thresholds

ENGINE_POLICY_SCHEMA = "hydra-framework.engine-policy.v1"
DELEGATION_POLICY_SCHEMA = "hydra-framework.delegation-policy.v1"

ENGINE_POLICY_FILE = "engine-policy.yaml"
DELEGATION_POLICY_FILE = "delegation-policy.yaml"

CAPABILITY_CLASSES = ("fast-default", "cheap-triage", "deep-reasoning", "large-context", "tool-heavy", "review-focused", "local-private")
EFFORT_ORDER = ("minimal", "low", "standard", "high", "max")
DEFAULT_ALLOWED_REASONS = ("inspection", "implementation-support", "review", "validation", "summarization")
DELEGATION_CONTROL_KEYS = ("generated_agent_policy", "generic_subagent_start_context", "effort_class_capping", "max_active_workers", "max_depth")
DELEGATION_CONTROL_STATES = ("supported", "advisory", "unsupported")
TUNABLE_THRESHOLD_DEFAULTS = {
    entry.key: entry.value
    for entry in thresholds.THRESHOLDS
    if entry.classification == thresholds.TEAM_TUNABLE_POLICY
}
ENGINE_INVARIANT_THRESHOLD_KEYS = frozenset(
    entry.key for entry in thresholds.THRESHOLDS if entry.classification == thresholds.ENGINE_INVARIANT
)


class ConfigError(ValueError):
    """A shared or private Hydra config file is invalid."""


@dataclasses.dataclass(frozen=True)
class ConfigPaths:
    root: Path
    hydra: Path
    local: Path

    def shared_engine_policy(self) -> Path: return self.hydra / "config" / ENGINE_POLICY_FILE
    def shared_delegation_policy(self) -> Path: return self.hydra / "config" / DELEGATION_POLICY_FILE
    def private_engine_policy(self) -> Path: return self.local / "config" / ENGINE_POLICY_FILE
    def private_delegation_policy(self) -> Path: return self.local / "config" / DELEGATION_POLICY_FILE


@dataclasses.dataclass(frozen=True)
class RolePolicy:
    allowed_capability_classes: tuple[str, ...]
    fallback_capability_class: str
    effort_ceiling: str


@dataclasses.dataclass(frozen=True)
class DelegationPolicy:
    enabled: bool
    max_active_workers: int
    max_depth: int
    allowed_reasons: tuple[str, ...]
    role_defaults: RolePolicy
    roles: dict[str, RolePolicy]


@dataclasses.dataclass(frozen=True)
class EffectiveConfig:
    thresholds: dict[str, int]
    delegation: DelegationPolicy


def load_effective_config(paths: ConfigPaths) -> EffectiveConfig:
    """Merge engine defaults, shared YAML, then tighten-only private YAML."""
    base = _default_config()
    shared = _merge_shared(base, paths)
    return _merge_private(shared, paths)


def validate_config(paths: ConfigPaths) -> list[Finding]:
    findings: list[Finding] = []
    for path, schema in [(paths.shared_engine_policy(), ENGINE_POLICY_SCHEMA), (paths.shared_delegation_policy(), DELEGATION_POLICY_SCHEMA)]:
        if not path.exists():
            label = display_path(path, paths.root)
            findings.append(Finding(path=label, code="config-policy", detail=f"{label} is missing"))
            continue
        try:
            data = parse_yaml(path, paths.root)
        except HydraYamlError as error:
            findings.append(Finding(path=display_path(path, paths.root), code="config-policy", detail=str(error)))
            continue
        if data.get("schema") != schema:
            label = display_path(path, paths.root)
            findings.append(Finding(path=label, code="config-policy", detail=f"{label} schema must be `{schema}`"))

    try:
        load_effective_config(paths)
    except ConfigError as error:
        label = _error_path(paths, str(error))
        findings.append(Finding(path=label, code="config-policy", detail=str(error)))
    return _unique_findings(findings)


def config_advisory_notes(paths: ConfigPaths) -> list[str]:
    try:
        effective = load_effective_config(paths)
    except ConfigError:
        return []
    return _role_advisory_notes(paths, effective) + _provider_support_notes(paths, effective.delegation)


def threshold_value(config: EffectiveConfig, key: str) -> int: return config.thresholds[key]
def threshold_default(key: str) -> int: return TUNABLE_THRESHOLD_DEFAULTS[key]


def delegation_policy(config: EffectiveConfig) -> DelegationPolicy:
    return config.delegation


def role_policy(policy: DelegationPolicy, role: str) -> RolePolicy:
    return policy.roles.get(role, policy.role_defaults)


def role_capability_class(config: EffectiveConfig, role: str, requested: str) -> str:
    policy = role_policy(config.delegation, role)
    if requested in policy.allowed_capability_classes:
        return requested
    return policy.fallback_capability_class


def role_effort_ceiling(config: EffectiveConfig, role: str, requested: str) -> str:
    policy = role_policy(config.delegation, role)
    if requested not in EFFORT_ORDER or policy.effort_ceiling not in EFFORT_ORDER:
        return requested
    return min(requested, policy.effort_ceiling, key=EFFORT_ORDER.index)


def delegation_instruction(config: EffectiveConfig, provider_controls: dict) -> str:
    policy = config.delegation
    advisory = sorted(key.replace("_", " ") for key in ("max_active_workers", "max_depth", "generic_subagent_start_context") if provider_controls.get(key) in {"advisory", "unsupported"})
    if not advisory:
        return ""
    enabled = "enabled" if policy.enabled else "disabled"
    return (
        "\n## Delegation Policy\n\n"
        f"Delegation is {enabled}. "
        f"Maximum active workers: {policy.max_active_workers}. "
        f"Maximum delegation depth: {policy.max_depth}. "
        f"Allowed reasons: {', '.join(policy.allowed_reasons)}. "
        f"This runtime cannot mechanically enforce: {', '.join(advisory)}; treat them as hard policy while operating.\n"
    )


def provider_delegation_controls(mapping: dict) -> dict:
    controls = yaml_map(mapping.get("delegation_controls"))
    return {key: yaml_str(controls.get(key)) for key in DELEGATION_CONTROL_KEYS}


def _default_config() -> EffectiveConfig:
    default_role = RolePolicy(CAPABILITY_CLASSES, "fast-default", "max")
    return EffectiveConfig(
        thresholds=dict(TUNABLE_THRESHOLD_DEFAULTS),
        delegation=DelegationPolicy(True, 2, 1, DEFAULT_ALLOWED_REASONS, default_role, {}),
    )


def _merge_shared(base: EffectiveConfig, paths: ConfigPaths) -> EffectiveConfig:
    engine = _read_yaml(paths.shared_engine_policy(), paths.root, required=False)
    delegation = _read_yaml(paths.shared_delegation_policy(), paths.root, required=False)
    thresholds_map = dict(base.thresholds)
    policy = base.delegation
    if engine:
        thresholds_map = _parse_engine_policy(engine, paths.shared_engine_policy(), paths.root, require_complete=True)
    if delegation:
        policy = _parse_delegation_policy(delegation, paths.shared_delegation_policy(), paths.root, base.delegation, require_complete=True)
    return EffectiveConfig(thresholds=thresholds_map, delegation=policy)


def _merge_private(base: EffectiveConfig, paths: ConfigPaths) -> EffectiveConfig:
    engine = _read_yaml(paths.private_engine_policy(), paths.root, required=False)
    delegation = _read_yaml(paths.private_delegation_policy(), paths.root, required=False)
    thresholds_map = dict(base.thresholds)
    policy = base.delegation
    if engine:
        private_thresholds = _parse_engine_policy(engine, paths.private_engine_policy(), paths.root, require_complete=False)
        for key, value in private_thresholds.items():
            if value > thresholds_map[key]:
                _fail(paths.private_engine_policy(), paths.root, f"`{key}` may only tighten from {thresholds_map[key]} to a lower positive value")
            thresholds_map[key] = value
    if delegation:
        private_policy = _parse_delegation_policy(delegation, paths.private_delegation_policy(), paths.root, base.delegation, require_complete=False)
        policy = _tighten_delegation(base.delegation, private_policy, paths.private_delegation_policy(), paths.root)
    return EffectiveConfig(thresholds=thresholds_map, delegation=policy)


def _read_yaml(path: Path, root: Path, *, required: bool) -> dict:
    try:
        return parse_yaml(path, root, required=required)
    except HydraYamlError as error:
        raise ConfigError(str(error)) from error


def _parse_engine_policy(data: dict, path: Path, root: Path, *, require_complete: bool) -> dict[str, int]:
    if data.get("schema") != ENGINE_POLICY_SCHEMA:
        _fail(path, root, f"{display_path(path, root)} schema must be `{ENGINE_POLICY_SCHEMA}`")
    _reject_unknown_keys(data, {"schema", "thresholds"}, path, root)
    raw_thresholds = yaml_map(data.get("thresholds"))
    if "thresholds" not in data or not isinstance(data.get("thresholds"), dict):
        _fail(path, root, f"{display_path(path, root)} `thresholds` must be a mapping")

    for key, value in raw_thresholds.items():
        if key in ENGINE_INVARIANT_THRESHOLD_KEYS:
            _fail(path, root, f"{display_path(path, root)} must not configure engine invariant threshold `{key}`")
        if key not in TUNABLE_THRESHOLD_DEFAULTS:
            _fail(path, root, f"{display_path(path, root)} has unknown threshold `{key}`")
        if not _is_positive_int(value):
            _fail(path, root, f"{display_path(path, root)} threshold `{key}` must be a positive integer")
    missing = sorted(set(TUNABLE_THRESHOLD_DEFAULTS) - set(raw_thresholds))
    if require_complete and missing:
        _fail(path, root, f"{display_path(path, root)} missing team-tunable threshold `{missing[0]}`")
    return {key: int(str(value).strip()) if isinstance(value, str) else value for key, value in raw_thresholds.items()}


def _parse_delegation_policy(data: dict, path: Path, root: Path, defaults: DelegationPolicy, *, require_complete: bool) -> DelegationPolicy:
    if data.get("schema") != DELEGATION_POLICY_SCHEMA:
        _fail(path, root, f"{display_path(path, root)} schema must be `{DELEGATION_POLICY_SCHEMA}`")
    _reject_unknown_keys(
        data,
        {"schema", "enabled", "max_active_workers", "max_depth", "allowed_reasons", "role_defaults", "roles"},
        path,
        root,
    )
    if require_complete:
        for key in ("role_defaults", "roles"):
            if key not in data or not isinstance(data.get(key), dict):
                _fail(path, root, f"{display_path(path, root)} `{key}` must be a mapping")
    enabled = _required_bool(data, "enabled", path, root) if require_complete or "enabled" in data else defaults.enabled
    max_active_workers = _required_positive_int(data, "max_active_workers", path, root) if require_complete or "max_active_workers" in data else defaults.max_active_workers
    max_depth = _required_positive_int(data, "max_depth", path, root) if require_complete or "max_depth" in data else defaults.max_depth
    allowed_reasons = tuple(yaml_list(data.get("allowed_reasons"))) if "allowed_reasons" in data else defaults.allowed_reasons
    if not allowed_reasons:
        _fail(path, root, f"{display_path(path, root)} `allowed_reasons` must not be empty")
    for reason in allowed_reasons:
        if reason not in DEFAULT_ALLOWED_REASONS:
            _fail(path, root, f"{display_path(path, root)} has unknown delegation reason `{reason}`")

    role_defaults = _parse_role_policy(yaml_map(data.get("role_defaults")), "role_defaults", path, root, defaults.role_defaults)
    raw_roles = yaml_map(data.get("roles"))
    roles = {
        str(name): _parse_role_policy(yaml_map(value), f"roles.{name}", path, root, defaults.roles.get(str(name), role_defaults))
        for name, value in raw_roles.items()
    }
    return DelegationPolicy(enabled, max_active_workers, max_depth, allowed_reasons, role_defaults, roles)


def _parse_role_policy(data: dict, label: str, path: Path, root: Path, defaults: RolePolicy) -> RolePolicy:
    if not data:
        return defaults
    _reject_unknown_keys(data, {"allowed_capability_classes", "fallback_capability_class", "effort_ceiling"}, path, root, prefix=label)
    allowed = tuple(yaml_list(data.get("allowed_capability_classes"))) or defaults.allowed_capability_classes
    for name in allowed:
        if name not in CAPABILITY_CLASSES:
            _fail(path, root, f"{display_path(path, root)} `{label}.allowed_capability_classes` has unknown class `{name}`")
    fallback = yaml_str(data.get("fallback_capability_class"), defaults.fallback_capability_class)
    if fallback not in allowed:
        _fail(path, root, f"{display_path(path, root)} `{label}.fallback_capability_class` must be in allowed_capability_classes")
    effort = yaml_str(data.get("effort_ceiling"), defaults.effort_ceiling)
    if effort not in EFFORT_ORDER:
        _fail(path, root, f"{display_path(path, root)} `{label}.effort_ceiling` must be one of {', '.join(EFFORT_ORDER)}")
    return RolePolicy(allowed, fallback, effort)


def _tighten_delegation(shared: DelegationPolicy, private: DelegationPolicy, path: Path, root: Path) -> DelegationPolicy:
    if shared.enabled is False and private.enabled is True:
        _fail(path, root, f"{display_path(path, root)} `enabled` may not loosen from false to true")
    if private.max_active_workers > shared.max_active_workers:
        _fail(path, root, f"{display_path(path, root)} `max_active_workers` may only decrease")
    if private.max_depth > shared.max_depth:
        _fail(path, root, f"{display_path(path, root)} `max_depth` may only decrease")
    if not set(private.allowed_reasons).issubset(shared.allowed_reasons):
        _fail(path, root, f"{display_path(path, root)} `allowed_reasons` may only be a subset")

    default_role = _tighten_role(shared.role_defaults, private.role_defaults, "role_defaults", path, root)
    roles: dict[str, RolePolicy] = {}
    for name, shared_role in shared.roles.items():
        roles[name] = _tighten_role(shared_role, private.roles.get(name, shared_role), f"roles.{name}", path, root)
    for name in set(private.roles) - set(shared.roles):
        roles[name] = _tighten_role(shared.role_defaults, private.roles[name], f"roles.{name}", path, root)
    return DelegationPolicy(private.enabled, private.max_active_workers, private.max_depth, private.allowed_reasons, default_role, roles)


def _tighten_role(shared: RolePolicy, private: RolePolicy, label: str, path: Path, root: Path) -> RolePolicy:
    if not set(private.allowed_capability_classes).issubset(shared.allowed_capability_classes):
        _fail(path, root, f"{display_path(path, root)} `{label}.allowed_capability_classes` may only be a subset")
    if private.fallback_capability_class not in private.allowed_capability_classes:
        _fail(path, root, f"{display_path(path, root)} `{label}.fallback_capability_class` must stay allowed")
    if EFFORT_ORDER.index(private.effort_ceiling) > EFFORT_ORDER.index(shared.effort_ceiling):
        _fail(path, root, f"{display_path(path, root)} `{label}.effort_ceiling` may only move downward")
    return private


def _role_advisory_notes(paths: ConfigPaths, config: EffectiveConfig) -> list[str]:
    notes: list[str] = []
    agents = paths.hydra / "capabilities/agents"
    if not agents.exists():
        return notes
    for metadata in sorted(agents.glob("*/metadata.yaml")):
        try:
            data = parse_yaml(metadata, paths.root)
        except HydraYamlError:
            continue
        role = yaml_str(data.get("name"), metadata.parent.name)
        requested = yaml_str(data.get("capability_class"))
        resolved = role_capability_class(config, role, requested)
        if requested and requested != resolved:
            notes.append(f"agent `{role}` requests capability class `{requested}` outside delegation policy; exporter uses `{resolved}`")
    return notes


def _provider_support_notes(paths: ConfigPaths, policy: DelegationPolicy) -> list[str]:
    if not policy.enabled:
        return []
    notes: list[str] = []
    for capability_map in sorted((paths.hydra / "adapters/providers").glob("*/capability-map.yaml")):
        try:
            data = parse_yaml(capability_map, paths.root)
        except HydraYamlError:
            continue
        provider = yaml_str(data.get("provider"), capability_map.parent.name)
        controls = yaml_map(data.get("delegation_controls"))
        advisory = [
            key.replace("_", "-")
            for key in ("generic_subagent_start_context", "max_active_workers", "max_depth")
            if controls.get(key) in {"advisory", "unsupported"}
        ]
        if advisory:
            notes.append(f"provider `{provider}` cannot mechanically enforce delegation controls: {', '.join(advisory)}")
    return notes


def _required_bool(data: dict, key: str, path: Path, root: Path) -> bool:
    if key not in data:
        _fail(path, root, f"{display_path(path, root)} missing `{key}`")
    value = data.get(key)
    if isinstance(value, bool):
        return value
    if isinstance(value, str) and value in {"true", "false"}:
        return value == "true"
    _fail(path, root, f"{display_path(path, root)} `{key}` must be true or false")


def _required_positive_int(data: dict, key: str, path: Path, root: Path) -> int:
    if key not in data or not _is_positive_int(data.get(key)):
        _fail(path, root, f"{display_path(path, root)} `{key}` must be a positive integer")
    value = data[key]
    return int(str(value).strip()) if isinstance(value, str) else value


def _is_positive_int(value: object) -> bool:
    if isinstance(value, bool):
        return False
    if isinstance(value, int):
        return value > 0
    return isinstance(value, str) and value.strip().isdigit() and int(value.strip()) > 0


def _reject_unknown_keys(data: dict, allowed: set[str], path: Path, root: Path, *, prefix: str = "") -> None:
    for key in data:
        if key not in allowed:
            label = f"{prefix}.`{key}`" if prefix else f"`{key}`"
            _fail(path, root, f"{display_path(path, root)} has unknown key {label}")


def _fail(path: Path, root: Path, detail: str) -> None:
    raise ConfigError(detail if display_path(path, root) in detail else f"{display_path(path, root)}: {detail}")


def _error_path(paths: ConfigPaths, detail: str) -> str:
    for path in [
        paths.shared_engine_policy(),
        paths.shared_delegation_policy(),
        paths.private_engine_policy(),
        paths.private_delegation_policy(),
    ]:
        label = display_path(path, paths.root)
        if label in detail:
            return label
    return display_path(paths.hydra / "config", paths.root)


def _unique_findings(findings: list[Finding]) -> list[Finding]:
    seen: set[tuple[str, str, str]] = set()
    unique: list[Finding] = []
    for finding in findings:
        key = (finding.path, finding.code, finding.detail)
        if key in seen:
            continue
        seen.add(key)
        unique.append(finding)
    return unique
