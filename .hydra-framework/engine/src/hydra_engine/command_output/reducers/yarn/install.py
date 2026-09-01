"""Reducer for `yarn install` output."""

from __future__ import annotations

from hydra_engine.command_output.model import CommandOutput, CommandOutputReducer, ParsedCommand, Reduction
from hydra_engine.command_output.reducers import selection


def matches(parsed: ParsedCommand) -> bool:
    tokens = tuple(token.lower() for token in parsed.significant_tokens)
    return len(tokens) > 1 and parsed.head in {"yarn", "pnpm"} and tokens[1] == "install"


def reduce(command_output: CommandOutput, max_lines: int):
    return Reduction(**selection.reduction_fields(command_output, "yarn-install", REDUCER.name, max_lines))


REDUCER = CommandOutputReducer("yarn-install", "yarn-install", selection.REDUCER_VERSION, matches, reduce)
