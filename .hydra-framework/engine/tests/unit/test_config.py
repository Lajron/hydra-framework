"""Unit tests for Hydra shared configuration policy."""

from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

_SRC = Path(__file__).resolve().parents[2] / "src"
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

from hydra_engine import config, thresholds  # noqa: E402


def _paths() -> config.ConfigPaths:
    root = Path(tempfile.mkdtemp(prefix="config-policy-"))
    return config.ConfigPaths(root=root, hydra=root / ".hydra-framework", local=root / ".hydra-framework.local")


def _write(root: Path, rel: str, content: str) -> None:
    target = root / rel
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(content, encoding="utf-8")


def _engine_policy(**overrides: int) -> str:
    values = {
        entry.key: entry.value
        for entry in thresholds.THRESHOLDS
        if entry.classification == thresholds.TEAM_TUNABLE_POLICY
    }
    values.update(overrides)
    lines = ["schema: hydra-framework.engine-policy.v1", "thresholds:"]
    lines.extend(f"  {key}: {value}" for key, value in sorted(values.items()))
    return "\n".join(lines) + "\n"


DELEGATION_POLICY = """schema: hydra-framework.delegation-policy.v1
enabled: true
max_active_workers: 2
max_depth: 1
allowed_reasons:
  - inspection
  - review
role_defaults:
  allowed_capability_classes:
    - fast-default
    - deep-reasoning
  fallback_capability_class: fast-default
  effort_ceiling: max
roles:
  demo:
    allowed_capability_classes:
      - deep-reasoning
    fallback_capability_class: deep-reasoning
    effort_ceiling: standard
"""


class ConfigLoadTests(unittest.TestCase):
    def test_missing_files_use_engine_defaults_for_runtime_loads(self):
        paths = _paths()
        effective = config.load_effective_config(paths)
        self.assertEqual(effective.delegation.max_active_workers, 2)
        self.assertEqual(
            config.threshold_value(effective, "hydra_engine.agent_hooks.token_budget.RETRY_MAX_ATTEMPTS_DEFAULT"),
            2,
        )

    def test_shared_config_overrides_engine_defaults(self):
        paths = _paths()
        _write(paths.root, ".hydra-framework/config/engine-policy.yaml", _engine_policy(
            **{"hydra_engine.agent_hooks.token_budget.RETRY_MAX_ATTEMPTS_DEFAULT": 1}
        ))
        _write(paths.root, ".hydra-framework/config/delegation-policy.yaml", DELEGATION_POLICY)
        effective = config.load_effective_config(paths)
        self.assertEqual(
            config.threshold_value(effective, "hydra_engine.agent_hooks.token_budget.RETRY_MAX_ATTEMPTS_DEFAULT"),
            1,
        )
        self.assertEqual(config.role_effort_ceiling(effective, "demo", "max"), "standard")

    def test_private_overrides_may_tighten(self):
        paths = _paths()
        _write(paths.root, ".hydra-framework/config/engine-policy.yaml", _engine_policy())
        _write(paths.root, ".hydra-framework/config/delegation-policy.yaml", DELEGATION_POLICY)
        _write(
            paths.root,
            ".hydra-framework.local/config/engine-policy.yaml",
            "schema: hydra-framework.engine-policy.v1\nthresholds:\n  hydra_engine.agent_hooks.token_budget.LARGE_LOG_LINES_DEFAULT: 10\n",
        )
        _write(
            paths.root,
            ".hydra-framework.local/config/delegation-policy.yaml",
            "schema: hydra-framework.delegation-policy.v1\nmax_active_workers: 1\nroles:\n  demo:\n    effort_ceiling: low\n",
        )
        effective = config.load_effective_config(paths)
        self.assertEqual(
            config.threshold_value(effective, "hydra_engine.agent_hooks.token_budget.LARGE_LOG_LINES_DEFAULT"),
            10,
        )
        self.assertEqual(effective.delegation.max_active_workers, 1)
        self.assertEqual(config.role_effort_ceiling(effective, "demo", "standard"), "low")

    def test_private_numeric_loosen_is_rejected(self):
        paths = _paths()
        _write(paths.root, ".hydra-framework/config/engine-policy.yaml", _engine_policy(
            **{"hydra_engine.agent_hooks.token_budget.RETRY_MAX_ATTEMPTS_DEFAULT": 1}
        ))
        _write(paths.root, ".hydra-framework/config/delegation-policy.yaml", DELEGATION_POLICY)
        _write(
            paths.root,
            ".hydra-framework.local/config/engine-policy.yaml",
            "schema: hydra-framework.engine-policy.v1\nthresholds:\n  hydra_engine.agent_hooks.token_budget.RETRY_MAX_ATTEMPTS_DEFAULT: 2\n",
        )
        with self.assertRaises(config.ConfigError):
            config.load_effective_config(paths)

    def test_private_delegation_loosen_is_rejected(self):
        paths = _paths()
        _write(paths.root, ".hydra-framework/config/engine-policy.yaml", _engine_policy())
        _write(paths.root, ".hydra-framework/config/delegation-policy.yaml", DELEGATION_POLICY)
        _write(paths.root, ".hydra-framework.local/config/delegation-policy.yaml", "schema: hydra-framework.delegation-policy.v1\nmax_depth: 3\n")
        with self.assertRaises(config.ConfigError):
            config.load_effective_config(paths)


class ConfigValidationTests(unittest.TestCase):
    def test_validate_requires_shared_files(self):
        findings = config.validate_config(_paths())
        self.assertTrue(any("engine-policy.yaml is missing" in finding.detail for finding in findings))
        self.assertTrue(any("delegation-policy.yaml is missing" in finding.detail for finding in findings))

    def test_shared_engine_policy_must_cover_every_team_tunable_threshold(self):
        paths = _paths()
        _write(
            paths.root,
            ".hydra-framework/config/engine-policy.yaml",
            "schema: hydra-framework.engine-policy.v1\nthresholds:\n  hydra_engine.agent_hooks.token_budget.RETRY_MAX_ATTEMPTS_DEFAULT: 2\n",
        )
        _write(paths.root, ".hydra-framework/config/delegation-policy.yaml", DELEGATION_POLICY)
        findings = config.validate_config(paths)
        self.assertTrue(any("missing team-tunable threshold" in finding.detail for finding in findings))

    def test_engine_policy_rejects_engine_invariant_unknown_and_bad_values(self):
        cases = [
            "hydra_engine.architecture.MAX_FAN_OUT: 8",
            "hydra_engine.nope.VALUE: 1",
            "hydra_engine.agent_hooks.token_budget.RETRY_MAX_ATTEMPTS_DEFAULT: no",
            "hydra_engine.agent_hooks.token_budget.RETRY_MAX_ATTEMPTS_DEFAULT: 0",
        ]
        for line in cases:
            with self.subTest(line=line):
                paths = _paths()
                _write(paths.root, ".hydra-framework/config/engine-policy.yaml", f"schema: hydra-framework.engine-policy.v1\nthresholds:\n  {line}\n")
                _write(paths.root, ".hydra-framework/config/delegation-policy.yaml", DELEGATION_POLICY)
                self.assertTrue(config.validate_config(paths))

    def test_delegation_policy_rejects_unknown_keys_and_bad_types(self):
        paths = _paths()
        _write(paths.root, ".hydra-framework/config/engine-policy.yaml", _engine_policy())
        _write(paths.root, ".hydra-framework/config/delegation-policy.yaml", DELEGATION_POLICY + "surprise: value\n")
        self.assertTrue(any("unknown key" in finding.detail for finding in config.validate_config(paths)))


class ConfigAdvisoryTests(unittest.TestCase):
    def test_disallowed_role_class_is_advisory_and_uses_fallback(self):
        paths = _paths()
        _write(paths.root, ".hydra-framework/config/engine-policy.yaml", _engine_policy())
        _write(paths.root, ".hydra-framework/config/delegation-policy.yaml", DELEGATION_POLICY)
        _write(paths.root, ".hydra-framework/capabilities/agents/demo/metadata.yaml", "name: demo\ncapability_class: cheap-triage\neffort: standard\n")
        notes = config.config_advisory_notes(paths)
        self.assertTrue(any("cheap-triage" in note and "deep-reasoning" in note for note in notes))

    def test_provider_enforcement_gaps_are_advisory(self):
        paths = _paths()
        _write(paths.root, ".hydra-framework/config/engine-policy.yaml", _engine_policy())
        _write(paths.root, ".hydra-framework/config/delegation-policy.yaml", DELEGATION_POLICY)
        _write(
            paths.root,
            ".hydra-framework/adapters/providers/claude/capability-map.yaml",
            "schema: hydra-framework.capability-map.v1\nprovider: claude\nverified: fixture\ncertainty: fixture\n"
            "delegation_controls:\n  generated_agent_policy: supported\n  generic_subagent_start_context: advisory\n  effort_class_capping: supported\n  max_active_workers: advisory\n  max_depth: advisory\n",
        )
        notes = config.config_advisory_notes(paths)
        self.assertTrue(any("provider `claude`" in note and "max-depth" in note for note in notes))


if __name__ == "__main__":
    unittest.main()
