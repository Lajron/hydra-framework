"""Reducer for Yarn type-check output."""

from __future__ import annotations

from hydra_engine.command_output.model import CommandOutput, CommandOutputReducer, ParsedCommand, Reduction
from hydra_engine.command_output.reducers import selection


def matches(parsed: ParsedCommand) -> bool:
    tokens = tuple(token.lower() for token in parsed.significant_tokens)
    words = set(tokens[1:])
    return parsed.head in {"yarn", "pnpm"} and bool({"check-types", "typecheck", "check", "tsc"} & words)


def reduce(command_output: CommandOutput, max_lines: int):
    return Reduction(**selection.reduction_fields(command_output, "yarn-check-types", REDUCER.name, max_lines))


REDUCER = CommandOutputReducer("yarn-check-types", "yarn-check-types", selection.REDUCER_VERSION, matches, reduce)
