"""Owner identity resolution."""

from __future__ import annotations

from hydra_engine.identity.slugs import slugify


class HydraOwnerError(RuntimeError):
    """Owner identity could not be resolved."""


def resolve_owner(explicit: str, env_owner: str, git_email: str) -> str:
    """Resolve who owns a personal task record.

    Order: explicit flag, `HYDRA_OWNER`, then `git config user.email` slugified
    in full, domain included. There is deliberately no default.

    git config is the primary source because every engineer has it configured
    before their first commit, and it is already the identity the team uses to
    answer "who did this" -- a second identity file could silently disagree with
    the commit author. `HYDRA_OWNER` overrides it for CI, containers, and shared
    machines where git identity is a service account.

    The full email is kept, not just the local part: Hydra is copied across
    host repos and organizations, and a local part alone (`example-owner`) can
    collide with an unrelated person of the same name in a different copy's
    domain. The full email is exactly as deterministic and
    costs nothing extra to slugify -- only a longer, less immediately readable
    slug.

    Unset is an error rather than `unknown`, because a default owner is how eight
    people end up writing into one directory. Failing here costs one `git config`
    command; a silent shared default costs a collision nobody can explain.
    """
    for candidate in (explicit, env_owner, git_email):
        candidate = (candidate or "").strip()
        if not candidate:
            continue
        return slugify(candidate)
    raise HydraOwnerError(
        "Hydra could not resolve an owner.\n"
        "Set one of:\n"
        "  git config user.email you@example.com   (preferred; matches your commits)\n"
        "  export HYDRA_OWNER=your-name            (CI, containers, shared machines)\n"
        "  --owner your-name                       (this command only)"
    )
