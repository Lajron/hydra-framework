"""Reducer for curl output."""

from __future__ import annotations

from hydra_engine.command_output.model import CommandOutput, CommandOutputReducer, ParsedCommand, Reduction
from hydra_engine.command_output.reducers import selection


def matches(parsed: ParsedCommand) -> bool:
    return parsed.head == "curl"


def reduce(command_output: CommandOutput, max_lines: int):
    return Reduction(**selection.reduction_fields(command_output, "curl-request", REDUCER.name, max_lines))


REDUCER = CommandOutputReducer("curl-request", "curl-request", selection.REDUCER_VERSION, matches, reduce)
