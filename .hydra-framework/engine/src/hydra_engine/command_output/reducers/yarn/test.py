"""Reducer for `yarn test` output."""

from __future__ import annotations

from hydra_engine.command_output.model import CommandOutput, CommandOutputReducer, ParsedCommand, Reduction
from hydra_engine.command_output.reducers import selection


def matches(parsed: ParsedCommand) -> bool:
    tokens = tuple(token.lower() for token in parsed.significant_tokens)
    return parsed.head in {"yarn", "pnpm"} and "test" in set(tokens[1:])


def reduce(command_output: CommandOutput, max_lines: int):
    return Reduction(**selection.reduction_fields(command_output, "yarn-test", REDUCER.name, max_lines))


REDUCER = CommandOutputReducer("yarn-test", "yarn-test", selection.REDUCER_VERSION, matches, reduce)
