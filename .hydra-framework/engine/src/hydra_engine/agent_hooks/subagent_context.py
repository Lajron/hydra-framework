"""Bounded discovery context for provider subagents."""

from __future__ import annotations

SUBAGENT_CONTEXT_AGENT_TYPES = ("general-purpose", "Explore", "Plan")
SUBAGENT_CONTEXT_MAX_PACKAGES_NAMED = 6
SUBAGENT_CONTEXT_TOKEN_BUDGET = 350


def build_subagent_context(
    package_names: list[str],
    token_budget: int = SUBAGENT_CONTEXT_TOKEN_BUDGET,
    chars_per_token: int = 4,
) -> str:
    """Return the provider-neutral Hydra pointers a generic subagent lacks."""
    packages = sorted(name for name in package_names if name)
    lines = [
        "Hydra repository context, supplied by a subagent-start hook.",
        "",
        "Canonical framework knowledge lives under `.hydra-framework/`. Use bounded Hydra commands before broad repository reads.",
        "",
        "Read-only entry points:",
        "- `python3 .hydra-framework/scripts/hydra.py knowledge-search \"<query>\" --budget <tokens>` returns ranked, cited snippets.",
        "- `python3 .hydra-framework/scripts/hydra.py delegation-brief \"<goal>\" --budget <tokens>` returns a read-first brief for delegated work.",
        "- `python3 .hydra-framework/scripts/hydra.py board` shows active Hydra task records.",
    ]
    if packages:
        shown = packages[:SUBAGENT_CONTEXT_MAX_PACKAGES_NAMED]
        remainder = len(packages) - len(shown)
        tail = f", and {remainder} more" if remainder else ""
        lines.append(f"- Knowledge packages: {', '.join(shown)}{tail}.")
    lines.extend(
        [
            "",
            "Stop rules:",
            "- If the bounded command output answers the task, stop there rather than widening scope.",
            "- If the pointers miss, say what is missing before reading more than roughly a dozen files.",
            "- Return verified facts with file citations; label inferences as inferences.",
        ]
    )
    return _fit_token_budget(lines, token_budget, chars_per_token)


def _fit_token_budget(lines: list[str], token_budget: int, chars_per_token: int) -> str:
    budget = max(token_budget, 1)
    divisor = max(chars_per_token, 1)
    kept: list[str] = []
    for line in lines:
        candidate = "\n".join([*kept, line])
        if _approx_tokens(candidate, divisor) > budget:
            break
        kept.append(line)
    if kept:
        return "\n".join(kept)
    return lines[0][:budget * divisor] if lines else ""


def _approx_tokens(text: str, chars_per_token: int) -> int:
    return max(1, (len(text) + chars_per_token - 1) // chars_per_token) if text else 0
