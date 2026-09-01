"""Mirror test for `hydra_engine.agent_hooks.token_budget`."""

from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

_SRC = Path(__file__).resolve().parents[3] / "src"
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

from hydra_engine.agent_hooks import token_budget  # noqa: E402
from hydra_engine import thresholds  # noqa: E402


class ReadJsonObjectTests(unittest.TestCase):
    def test_missing_file_returns_empty_dict(self):
        missing = Path(tempfile.mkdtemp(prefix="token-budget-")) / "missing.json"
        self.assertEqual(token_budget.read_json_object(missing), {})

    def test_non_object_json_returns_empty_dict(self):
        path = Path(tempfile.mkdtemp(prefix="token-budget-")) / "list.json"
        path.write_text("[1, 2]", encoding="utf-8")
        self.assertEqual(token_budget.read_json_object(path), {})

    def test_invalid_json_returns_empty_dict(self):
        path = Path(tempfile.mkdtemp(prefix="token-budget-")) / "bad.json"
        path.write_text("not json", encoding="utf-8")
        self.assertEqual(token_budget.read_json_object(path), {})


class TokenHookPolicyTests(unittest.TestCase):
    def test_defaults_when_no_config_given(self):
        local = Path(tempfile.mkdtemp(prefix="token-budget-"))
        policy = token_budget.token_hook_policy(None, local)
        self.assertEqual(policy, token_budget.DEFAULT_TOKEN_HOOK_POLICY)

    def test_explicit_path_overrides_defaults(self):
        local = Path(tempfile.mkdtemp(prefix="token-budget-"))
        config = local / "policy.json"
        config.write_text(json.dumps({"context_budget_tokens": 5000}), encoding="utf-8")
        policy = token_budget.token_hook_policy(str(config), local)
        self.assertEqual(policy["context_budget_tokens"], 5000)
        self.assertEqual(policy["retry_max_attempts"], 2)

    def test_shared_yaml_supplies_numeric_defaults(self):
        root = Path(tempfile.mkdtemp(prefix="token-budget-"))
        hydra = root / ".hydra-framework"
        local = root / ".hydra-framework.local"
        values = {
            entry.key: entry.value
            for entry in thresholds.THRESHOLDS
            if entry.classification == thresholds.TEAM_TUNABLE_POLICY
        }
        values["hydra_engine.agent_hooks.token_budget.RETRY_MAX_ATTEMPTS_DEFAULT"] = 1
        lines = ["schema: hydra-framework.engine-policy.v1", "thresholds:"]
        lines.extend(f"  {key}: {value}" for key, value in sorted(values.items()))
        engine = hydra / "config/engine-policy.yaml"
        engine.parent.mkdir(parents=True, exist_ok=True)
        engine.write_text("\n".join(lines) + "\n", encoding="utf-8")
        (hydra / "config/delegation-policy.yaml").write_text(
            "schema: hydra-framework.delegation-policy.v1\n"
            "enabled: true\nmax_active_workers: 2\nmax_depth: 1\n"
            "allowed_reasons:\n  - inspection\n"
            "role_defaults:\n  allowed_capability_classes:\n    - fast-default\n  fallback_capability_class: fast-default\n  effort_ceiling: max\n"
            "roles: {}\n",
            encoding="utf-8",
        )
        policy = token_budget.token_hook_policy(None, local, hydra)
        self.assertEqual(policy["retry_max_attempts"], 1)

    def test_default_private_json_no_longer_overrides_governed_numbers(self):
        root = Path(tempfile.mkdtemp(prefix="token-budget-"))
        local = root / ".hydra-framework.local"
        token_config = local / "monitoring/token-hooks.json"
        token_config.parent.mkdir(parents=True, exist_ok=True)
        token_config.write_text(json.dumps({"retry_max_attempts": 9, "store_full_logs": True}), encoding="utf-8")
        policy = token_budget.token_hook_policy(None, local)
        self.assertEqual(policy["retry_max_attempts"], 2)
        self.assertTrue(policy["store_full_logs"])


class PolicyAccessorTests(unittest.TestCase):
    def test_policy_int_falls_back_on_wrong_type(self):
        self.assertEqual(token_budget.policy_int({"n": "not-an-int"}, "n", 7), 7)
        self.assertEqual(token_budget.policy_int({"n": 9}, "n", 7), 9)

    def test_policy_bool_falls_back_on_wrong_type(self):
        self.assertEqual(token_budget.policy_bool({"b": "yes"}, "b", False), False)
        self.assertEqual(token_budget.policy_bool({"b": True}, "b", False), True)


class ConfiguredContextBudgetTests(unittest.TestCase):
    def test_cli_budget_wins_over_policy(self):
        self.assertEqual(token_budget.configured_context_budget({"context_budget_tokens": 100}, 50), 50)

    def test_policy_budget_used_when_cli_omitted(self):
        self.assertEqual(token_budget.configured_context_budget({"context_budget_tokens": 100}, None), 100)

    def test_non_positive_policy_budget_is_ignored(self):
        self.assertIsNone(token_budget.configured_context_budget({"context_budget_tokens": 0}, None))
        self.assertIsNone(token_budget.configured_context_budget({}, None))


if __name__ == "__main__":
    unittest.main()
