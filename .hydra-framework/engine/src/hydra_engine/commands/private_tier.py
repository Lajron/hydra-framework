"""Command for bootstrapping Hydra's private local tier."""

from __future__ import annotations

import json

from hydra_engine.agent_hooks.token_budget import DEFAULT_TOKEN_HOOK_POLICY
from hydra_engine.commands import CommandResult
from hydra_engine.documents.tokens import display_path, write_text
from hydra_engine.installation.private_tier import (
    ensure_gitignore_rule,
    ensure_private_tier,
    gitignore_rule_present,
    private_tier_ignored,
)


def _write_token_policy(root, local) -> str:
    path = local / "monitoring" / "token-hooks.json"
    if path.exists():
        return "already-present"
    write_text(path, json.dumps(DEFAULT_TOKEN_HOOK_POLICY, indent=2, sort_keys=True) + "\n")
    return "written"


def command_init_local(args, paths) -> CommandResult:
    """Seed this repository's private local tier."""
    local = paths.root / ".hydra-framework.local"
    rule_present = gitignore_rule_present(paths.root)
    ignored = private_tier_ignored(paths.root)

    if args.check:
        print("Hydra init-local check")
        print(f"- gitignore rule: {'present' if rule_present else 'missing'}")
        print(f"- private tier ignored: {'yes' if ignored else 'no'}")
        print(f"- private tier directory: {'present' if local.exists() else 'absent'}")
        return CommandResult(0 if rule_present and ignored else 1)

    gitignore_status = ensure_gitignore_rule(paths.root)
    seed = ensure_private_tier(paths.root, local)
    print("Hydra init-local: private tier ready")
    print(f"- gitignore rule: {gitignore_status}")
    print(f"- private tier ignored: {'yes' if private_tier_ignored(paths.root) else 'no'}")
    print(f"- directories created: {len(seed['created'])}")
    print(f"- directories already present: {len(seed['existing'])}")
    print(f"- seed files written: {len(seed['seeded'])}")
    for rel in seed["seeded"]:
        print(f"  - {rel}")

    if args.write_token_policy:
        status = _write_token_policy(paths.root, local)
        print(f"- token hook policy: {status} at {display_path(local / 'monitoring' / 'token-hooks.json', paths.root)}")

    print("See .hydra-framework/repo/knowledge/state-tiers.md for the private tier shape.")
    return CommandResult(0)


def register(subparsers) -> None:
    init_local = subparsers.add_parser("init-local", help="Seed this repository's ignored private local tier")
    init_local.add_argument("--check", action="store_true", help="Report whether the private tier is ignored without writing")
    init_local.add_argument(
        "--write-token-policy",
        action="store_true",
        help="Write the default private token hook policy if it is absent",
    )
    init_local.set_defaults(func=_dispatch_init_local)


def _dispatch_init_local(args, ctx) -> int:
    return command_init_local(args, ctx.installation_paths()).exit_code
