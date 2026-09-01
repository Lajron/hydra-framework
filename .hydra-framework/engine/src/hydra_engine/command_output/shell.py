"""Shell command parsing for command-output reducers."""

from __future__ import annotations

import dataclasses
import re
import shlex
from pathlib import Path

CONTROL_OPERATORS = frozenset({"&&", "||", ";"})
CARRIER_HEADS = frozenset({"cd", "pushd", "popd", "export", "source", "set", "unset", "."})


@dataclasses.dataclass(frozen=True)
class ShellCommand:
    command: str
    tokens: tuple[str, ...]
    segments: tuple[tuple[str, ...], ...]
    meaningful_segments: tuple[tuple[str, ...], ...]

    @property
    def significant_tokens(self) -> tuple[str, ...]:
        if self.meaningful_segments:
            return self.meaningful_segments[0]
        return strip_env_prefix(self.tokens)

    @property
    def head(self) -> str:
        tokens = self.significant_tokens
        return Path(tokens[0]).name if tokens else ""


def shell_tokens(command: str) -> tuple[str, ...]:
    try:
        lexer = shlex.shlex(command, posix=True, punctuation_chars=True)
        lexer.whitespace_split = True
        return tuple(lexer)
    except ValueError:
        return tuple(command.split())


def strip_env_prefix(tokens: tuple[str, ...]) -> tuple[str, ...]:
    remaining = list(tokens)
    while remaining and _is_env_assignment(remaining[0]):
        remaining.pop(0)
    if remaining and remaining[0] == "env":
        remaining.pop(0)
        while remaining and _is_env_assignment(remaining[0]):
            remaining.pop(0)
    return tuple(remaining)


def split_top_level_segments(command: str) -> tuple[tuple[str, ...], ...]:
    segments: list[list[str]] = [[]]
    for token in shell_tokens(command):
        if token in CONTROL_OPERATORS:
            segments.append([])
        else:
            segments[-1].append(token)
    return tuple(tuple(segment) for segment in segments if segment)


def meaningful_segments(command: str) -> tuple[tuple[str, ...], ...]:
    result: list[tuple[str, ...]] = []
    for segment in split_top_level_segments(command):
        tokens = strip_env_prefix(segment)
        if not tokens:
            continue
        if Path(tokens[0]).name in CARRIER_HEADS:
            continue
        result.append(tokens)
    return tuple(result)


def parse_command(command: str) -> ShellCommand:
    return ShellCommand(
        command=command,
        tokens=shell_tokens(command),
        segments=split_top_level_segments(command),
        meaningful_segments=meaningful_segments(command),
    )


def git_subcommand(tokens: tuple[str, ...]) -> str:
    index = 1
    while index < len(tokens):
        token = tokens[index]
        if token in {"-C", "-c", "--git-dir", "--work-tree"}:
            index += 2
            continue
        if token.startswith("-"):
            index += 1
            continue
        return token
    return ""


def _is_env_assignment(token: str) -> bool:
    if token.startswith("-") or "=" not in token:
        return False
    key, _value = token.split("=", 1)
    return re.match(r"^[A-Za-z_][A-Za-z0-9_]*$", key) is not None

