"""Reducer for `npm run build` output."""

from __future__ import annotations

from hydra_engine.command_output.model import CommandOutput, CommandOutputReducer, ParsedCommand, Reduction
from hydra_engine.command_output.reducers import selection


def matches(parsed: ParsedCommand) -> bool:
    tokens = tuple(token.lower() for token in parsed.significant_tokens)
    return parsed.head == "npm" and "build" in set(tokens[1:])


def reduce(command_output: CommandOutput, max_lines: int):
    return Reduction(**selection.reduction_fields(command_output, "npm-build", REDUCER.name, max_lines))


REDUCER = CommandOutputReducer("npm-build", "npm-build", selection.REDUCER_VERSION, matches, reduce)
