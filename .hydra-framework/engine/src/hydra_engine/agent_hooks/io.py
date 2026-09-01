"""Stdin/file reading and private log storage.

Moved unchanged from `scripts/hydra.py`, with `LOCAL` replaced by an explicit
`AgentHooksPaths` argument.
"""

from __future__ import annotations

import sys
from pathlib import Path

from hydra_engine.agent_hooks.paths import AgentHooksPaths
from hydra_engine.documents.tokens import read_text, write_text
from hydra_engine.identity.slugs import slugify
from hydra_engine.ports import clock


def read_stdin_or_file(path_value: str | None) -> str:
    if path_value:
        return read_text(Path(path_value).resolve())
    return sys.stdin.read()


def store_private_log(paths: AgentHooksPaths, text: str, name_hint: str) -> Path:
    stamp = clock.filename_stamp()
    name = slugify(name_hint or "log")
    target = paths.local / "logs" / f"{stamp}-{name}.log"
    write_text(target, text)
    return target
