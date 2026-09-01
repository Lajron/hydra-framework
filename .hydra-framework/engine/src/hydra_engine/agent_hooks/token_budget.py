"""Token-hook policy and budget decisions.

Moved unchanged from `scripts/hydra.py`, with the default policy path made an
explicit argument instead of reading the `LOCAL` global.
"""

from __future__ import annotations

import json
from pathlib import Path

from hydra_engine.config import ConfigPaths, load_effective_config, threshold_value
from hydra_engine.documents.tokens import read_text

LARGE_LOG_LINES_DEFAULT = 120
LARGE_LOG_CHARS_DEFAULT = 20000
SUMMARY_MAX_LINES_DEFAULT = 80
RETRY_MAX_ATTEMPTS_DEFAULT = 2

DEFAULT_TOKEN_HOOK_POLICY = {
    "context_budget_tokens": None,
    "include_generated_skills": False,
    "large_log_lines": LARGE_LOG_LINES_DEFAULT,
    "large_log_chars": LARGE_LOG_CHARS_DEFAULT,
    "summary_max_lines": SUMMARY_MAX_LINES_DEFAULT,
    "retry_max_attempts": RETRY_MAX_ATTEMPTS_DEFAULT,
    "store_full_logs": False,
}

THRESHOLD_KEYS = {
    "large_log_lines": "hydra_engine.agent_hooks.token_budget.LARGE_LOG_LINES_DEFAULT",
    "large_log_chars": "hydra_engine.agent_hooks.token_budget.LARGE_LOG_CHARS_DEFAULT",
    "summary_max_lines": "hydra_engine.agent_hooks.token_budget.SUMMARY_MAX_LINES_DEFAULT",
    "retry_max_attempts": "hydra_engine.agent_hooks.token_budget.RETRY_MAX_ATTEMPTS_DEFAULT",
}

LOCAL_ONLY_KEYS = {"context_budget_tokens", "include_generated_skills", "store_full_logs"}


def read_json_object(path: Path) -> dict:
    if not path.exists():
        return {}
    try:
        value = json.loads(read_text(path))
    except json.JSONDecodeError:
        return {}
    return value if isinstance(value, dict) else {}


def token_hook_policy(path_value: str | None, local: Path, hydra: Path | None = None) -> dict:
    if path_value:
        path = Path(path_value).resolve()
        policy = dict(DEFAULT_TOKEN_HOOK_POLICY)
        policy.update(read_json_object(path))
        return policy

    policy = dict(DEFAULT_TOKEN_HOOK_POLICY)
    if hydra is not None:
        config = load_effective_config(ConfigPaths(root=hydra.parent, hydra=hydra, local=local))
        for policy_key, threshold_key in THRESHOLD_KEYS.items():
            policy[policy_key] = threshold_value(config, threshold_key)
    private_policy = read_json_object(local / "monitoring" / "token-hooks.json")
    policy.update({key: value for key, value in private_policy.items() if key in LOCAL_ONLY_KEYS})
    return policy


def policy_int(policy: dict, key: str, fallback: int) -> int:
    value = policy.get(key, fallback)
    return value if isinstance(value, int) else fallback


def policy_bool(policy: dict, key: str, fallback: bool) -> bool:
    value = policy.get(key, fallback)
    return value if isinstance(value, bool) else fallback


def configured_context_budget(policy: dict, cli_budget: int | None) -> int | None:
    if cli_budget is not None:
        return cli_budget
    value = policy.get("context_budget_tokens")
    return value if isinstance(value, int) and value > 0 else None
