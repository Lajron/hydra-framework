"""Reducer for ripgrep search output."""

from __future__ import annotations

from hydra_engine.command_output.model import CommandOutput, CommandOutputReducer, ParsedCommand, Reduction
from hydra_engine.command_output.reducers import selection


def matches(parsed: ParsedCommand) -> bool:
    return parsed.head == "rg"


def reduce(command_output: CommandOutput, max_lines: int):
    return Reduction(**selection.reduction_fields(command_output, "ripgrep-search", REDUCER.name, max_lines))


REDUCER = CommandOutputReducer("ripgrep-search", "ripgrep-search", selection.REDUCER_VERSION, matches, reduce)
