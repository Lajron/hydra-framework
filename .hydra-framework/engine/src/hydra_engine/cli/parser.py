"""Argparse construction.

Each command module passed in exposes `register(subparsers)`, adding its
own subcommand(s) and wiring `set_defaults(func=...)` to a
`(args, ctx) -> int` wrapper defined in that same module. `build_parser`
just iterates the given modules instead of being a large per-command
switchboard. The modules themselves are a `cli.dispatch` concern, not this
one: importing all nine here would put this module's own fan-out over
check 5's cap of 8, and only the declared composition root is exempt.

`extra`, if given, is called last with the same `subparsers` object: it is
how `scripts/hydra.py` registers the ten commands still dispatched through
its own globals (see `cli.dispatch`'s docstring).
"""

from __future__ import annotations

import argparse
from typing import Callable, Sequence


def build_parser(
    command_modules: Sequence[object],
    extra: "Callable[[argparse._SubParsersAction], None] | None" = None,
) -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="hydra.py", description="Hydra framework helper")
    sub = parser.add_subparsers(dest="command", required=True)
    for module in command_modules:
        module.register(sub)
    if extra is not None:
        extra(sub)
    return parser
