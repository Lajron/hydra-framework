"""Reducer for `dotnet build` output."""

from __future__ import annotations

from hydra_engine.command_output.model import CommandOutput, CommandOutputReducer, ParsedCommand, Reduction
from hydra_engine.command_output.reducers import selection


def matches(parsed: ParsedCommand) -> bool:
    tokens = tuple(token.lower() for token in parsed.significant_tokens)
    return len(tokens) > 1 and parsed.head == "dotnet" and tokens[1] == "build"


def reduce(command_output: CommandOutput, max_lines: int):
    return Reduction(**selection.reduction_fields(command_output, "dotnet-build", REDUCER.name, max_lines))


REDUCER = CommandOutputReducer("dotnet-build", "dotnet-build", selection.REDUCER_VERSION, matches, reduce)
