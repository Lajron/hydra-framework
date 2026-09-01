"""Command-output contract harness.

Builds a sealed fixture Hydra tree in a tmpdir, drives `hydra.main` through
the `RepoContext` injection point (Milestone 0, step 1) — not global
patching — and reports exit code, stdout, stderr, and a sha256 manifest of
every file under the fixture root. That manifest is what later phases diff
against a pre-move capture to prove a refactor step is byte-identical.
"""

from __future__ import annotations

import contextlib
import dataclasses
import hashlib
import io
import os
import sys
import tempfile
from pathlib import Path
from typing import Callable

_SCRIPTS_DIR = Path(__file__).resolve().parents[3] / "scripts"
if str(_SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS_DIR))

import hydra  # noqa: E402

RECORD_GOLDEN_ENV = "HYDRA_RECORD_GOLDEN"


@dataclasses.dataclass(frozen=True)
class CommandOutcome:
    exit_code: int
    stdout: str
    stderr: str
    manifest: dict[str, str | None]


def _manifest(root: Path) -> dict[str, str]:
    return {
        str(path.relative_to(root)): hashlib.sha256(path.read_bytes()).hexdigest()
        for path in sorted(root.rglob("*"))
        if path.is_file()
    }


def run_command(
    argv: list[str],
    fixture: dict[str, str] | None = None,
    ctx: "hydra.RepoContext | None" = None,
    pre_run: Callable[[Path], None] | None = None,
) -> CommandOutcome:
    """Run one `hydra.py` command against a sealed fixture tree.

    `fixture` is a relative-path -> text-content map written into the tmp
    root before the command runs. `ctx`, if given, overrides the default
    `RepoContext.for_root(tmp_root)` (e.g. to point one path at a second
    fixture tree for a cross-tier test). `pre_run`, if given, is called with
    the tmp root after the fixture is written and before the command runs —
    for setup a text fixture can't express, such as `git init` for a golden
    that needs a real git repository underneath it.
    """
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        for rel_path, content in (fixture or {}).items():
            target = root / rel_path
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(content)
        if pre_run is not None:
            pre_run(root)

        run_ctx = ctx or hydra.RepoContext.for_root(root)
        before = _manifest(root)

        stdout, stderr = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
            exit_code = hydra.main(argv, ctx=run_ctx)

        after = _manifest(root)
        manifest: dict[str, str | None] = dict(after)
        for path in before:
            if path not in after:
                manifest[path] = None

        return CommandOutcome(exit_code=exit_code, stdout=stdout.getvalue(), stderr=stderr.getvalue(), manifest=manifest)


def recording_enabled() -> bool:
    return os.environ.get(RECORD_GOLDEN_ENV) == "1"
