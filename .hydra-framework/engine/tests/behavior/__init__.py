"""Behavioral checks: concurrency scenarios that need a real subprocess (git, a forked process)
rather than an injected interleaving, so they don't fit the per-module unit
mirror rule under `tests/unit/` or the live-repository invariants under
`tests/repository/`."""
