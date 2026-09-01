"""Agent-hook command logic.

Log summaries, retry-failure fingerprinting, and token-budget policy for the
hooks Claude Code invokes on every prompt/edit/command result. `hook-post-edit`
is not here: it calls nothing this package owns (its notice branches reach
`work.placement` and `providers.reclaim` instead), so it lives in its own
`hydra_engine.commands.hooks` module rather than `commands.agent_hooks` --
see that module's docstring.
"""

from __future__ import annotations
