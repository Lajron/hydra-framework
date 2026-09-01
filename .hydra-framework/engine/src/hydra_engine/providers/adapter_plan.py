"""The one planner every provider-surface command reads.

Reads `providers.capabilities.PROVIDERS` (the fourth extension
registry) rather than branching on provider slug: which renderer builds a
provider's agent wrapper is `Provider.build_agent_wrapper`, a field on the
registry entry, not an `if provider == "codex":` this planner used to carry.
"""

from __future__ import annotations

from pathlib import Path

from hydra_engine.config import ConfigPaths, load_effective_config
from hydra_engine.providers.capabilities import PROVIDERS, build_skill_wrapper, capability_map
from hydra_engine.providers.paths import ProvidersPaths


def planned_adapter_files(paths: ProvidersPaths) -> dict[Path, str]:
    """Every provider file that export-adapters owns, mapped to its content.

    One planner drives generate, dry-run, drift-check, and orphan detection, so
    those four can never disagree about what is generated.
    """
    plan: dict[Path, str] = {}
    skill_dirs = sorted(
        path for path in paths.skills_root().glob("*") if (path / "skill.md").exists()
    )
    agent_dirs = sorted(
        path for path in paths.agents_root().glob("*") if (path / "agent.md").exists()
    )
    config = load_effective_config(ConfigPaths(root=paths.root, hydra=paths.hydra, local=paths.root / ".hydra-framework.local"))

    for provider in PROVIDERS:
        mapping = capability_map(paths, provider.slug)
        for skill_dir in skill_dirs:
            wrapper_name, files = build_skill_wrapper(skill_dir, provider.slug, paths.root)
            for filename, content in files.items():
                plan[paths.root / provider.skills_target / wrapper_name / filename] = content
        if provider.agents_target is None:
            continue
        for agent_dir in agent_dirs:
            wrapper_name, files = provider.build_agent_wrapper(agent_dir, provider.slug, mapping, paths.root, config)
            for filename, content in files.items():
                plan[paths.root / provider.agents_target / filename] = content
    return plan
