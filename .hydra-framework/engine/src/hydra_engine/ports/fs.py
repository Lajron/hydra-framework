"""Filesystem write port.

The two primitives that let a caller eliminate read-modify-write instead of
serializing it: `append_line` for accumulating state (a counter that is
appended to cannot be lost by a concurrent writer; aggregate at read time),
and `create_exclusive` for a create-only write that closes the classic
`exists()`-then-write TOCTOU window at the OS level.

`_before_append` is a test-only seam, same pattern as `ports.clock`/
`ports.uids`/`documents.tokens._before_replace`: tests patch it to run a
competing `append_line` between this call's open and its write, to prove
concurrent appends interleave as intact lines rather than corrupting or
losing each other, with no threads.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Callable

_before_append: Callable[[Path], None] | None = None


def append_line(path: Path, line: str) -> None:
    """Append one line to `path`, creating it if needed.

    A single `os.write()` in `O_APPEND` mode is atomic with respect to other
    writers as long as it fits within one filesystem write (see callers'
    line-size budgets), so two processes appending at once each land their
    line intact, never interleaved or torn.
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    data = (line if line.endswith("\n") else line + "\n").encode("utf-8")
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_APPEND, 0o666)
    try:
        if _before_append is not None:
            _before_append(path)
        os.write(fd, data)
    finally:
        os.close(fd)


def create_exclusive(path: Path, content: str) -> bool:
    """Create `path` with `content` only if it does not already exist.

    Returns False without writing anything if it does. `O_EXCL` makes the
    existence check and the creation a single atomic OS operation, so two
    racing callers can never both believe they created the file.
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o666)
    except FileExistsError:
        return False
    try:
        os.write(fd, content.encode("utf-8"))
    finally:
        os.close(fd)
    return True
