"""Capability scaffolding command decisions."""

from __future__ import annotations

from hydra_engine.capability_scaffold import agent_body_text, agent_metadata_text, skill_body_text, skill_metadata_text
from hydra_engine.commands import CommandResult, references
from hydra_engine.config import CAPABILITY_CLASSES, EFFORT_ORDER
from hydra_engine.documents.tokens import write_text
from hydra_engine.identity.slugs import slugify
from hydra_engine.ports import uids


def _title(name: str, explicit_title: str) -> str:
    return explicit_title or name.replace("-", " ").replace("_", " ").title()


def _scaffold(target, metadata: str, body_name: str, body: str, root, force: bool, label: str) -> CommandResult:
    if target.exists() and not force:
        print(f"Capability {label} already exists: {target.relative_to(root)}")
        return CommandResult(1)
    write_text(target / "metadata.yaml", metadata)
    write_text(target / body_name, body)
    print(f"Created capability {label}: {target.relative_to(root)}")
    print(f"- {(target / 'metadata.yaml').relative_to(root)}")
    print(f"- {(target / body_name).relative_to(root)}")
    return CommandResult(0)


def command_capability_scaffold_skill(args, paths) -> CommandResult:
    name = slugify(args.name)
    return _scaffold(
        paths.skills_root() / name,
        skill_metadata_text(name, args.description, uids.new_uid(), args.kind),
        "skill.md",
        skill_body_text(_title(args.name, args.title)),
        paths.root,
        args.force,
        "skill",
    )


def command_capability_scaffold_agent(args, paths) -> CommandResult:
    name = slugify(args.name)
    return _scaffold(
        paths.agents_root() / name,
        agent_metadata_text(name, args.description, uids.new_uid(), args.capability_class, args.effort),
        "agent.md",
        agent_body_text(_title(args.name, args.title)),
        paths.root,
        args.force,
        "agent",
    )


def register(subparsers) -> None:
    """Add `capability scaffold-skill` and `capability scaffold-agent`."""
    capability = subparsers.add_parser("capability", help="Create canonical capability modules")
    capability_sub = capability.add_subparsers(dest="capability_command", required=True)

    skill = capability_sub.add_parser("scaffold-skill", help="Create a canonical skill module")
    skill.add_argument("name")
    skill.add_argument("--description", required=True)
    skill.add_argument("--kind", choices=("procedure", "command"), default="procedure")
    skill.add_argument("--title", default="")
    skill.add_argument("--force", action="store_true")
    skill.set_defaults(func=_dispatch_scaffold_skill)

    agent = capability_sub.add_parser("scaffold-agent", help="Create a canonical agent module")
    agent.add_argument("name")
    agent.add_argument("--description", required=True)
    agent.add_argument("--capability-class", choices=CAPABILITY_CLASSES, required=True)
    agent.add_argument("--effort", choices=EFFORT_ORDER, required=True)
    agent.add_argument("--title", default="")
    agent.add_argument("--force", action="store_true")
    agent.set_defaults(func=_dispatch_scaffold_agent)


def _dispatch_scaffold_skill(args, ctx) -> int:
    result = command_capability_scaffold_skill(args, ctx.providers_paths())
    return result.exit_code or references.command_ref_index(args, ctx.resolver_paths()).exit_code


def _dispatch_scaffold_agent(args, ctx) -> int:
    result = command_capability_scaffold_agent(args, ctx.providers_paths())
    return result.exit_code or references.command_ref_index(args, ctx.resolver_paths()).exit_code
