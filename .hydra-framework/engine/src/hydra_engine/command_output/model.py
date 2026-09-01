"""Shared command-output reducer model."""

from __future__ import annotations

import dataclasses
from pathlib import Path
from typing import Callable, Protocol


class ParsedCommand(Protocol):
    command: str
    significant_tokens: tuple[str, ...]
    head: str


@dataclasses.dataclass(frozen=True)
class CommandOutput:
    provider: str
    tool_name: str
    command: str
    cwd: str
    exit_code: int | None
    output: str
    session_id: str = ""
    key: str = ""
    raw_output_path: Path | None = None

    @property
    def line_count(self) -> int:
        return len(self.output.splitlines())

    @property
    def char_count(self) -> int:
        return len(self.output)


@dataclasses.dataclass(frozen=True)
class Reduction:
    schema: str
    provider: str
    tool_name: str
    command: str
    cwd: str
    exit_code: int | None
    family: str
    reducer_name: str
    reducer_version: str
    compact_summary: str
    important_lines: tuple[str, ...]
    omitted_lines: int
    omitted_chars: int
    input_line_count: int
    input_char_count: int
    session_id: str = ""
    key: str = ""

    @property
    def has_reducer(self) -> bool:
        return self.reducer_name not in {"", "none"}


@dataclasses.dataclass(frozen=True)
class CommandOutputReducer:
    name: str
    family: str
    version: str
    matches: Callable[[ParsedCommand], bool]
    reduce: Callable[[CommandOutput, int], Reduction]

