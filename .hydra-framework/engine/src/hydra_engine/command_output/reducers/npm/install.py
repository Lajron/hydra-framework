"""Reducer for `npm install` output."""

from __future__ import annotations

from hydra_engine.command_output.model import CommandOutput, CommandOutputReducer, ParsedCommand, Reduction
from hydra_engine.command_output.reducers import selection


def matches(parsed: ParsedCommand) -> bool:
    tokens = tuple(token.lower() for token in parsed.significant_tokens)
    return len(tokens) > 1 and parsed.head == "npm" and tokens[1] in {"install", "i", "ci"}


def reduce(command_output: CommandOutput, max_lines: int):
    return Reduction(**selection.reduction_fields(command_output, "npm-install", REDUCER.name, max_lines))


REDUCER = CommandOutputReducer("npm-install", "npm-install", selection.REDUCER_VERSION, matches, reduce)
