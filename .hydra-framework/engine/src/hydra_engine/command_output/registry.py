"""Explicit command-output reducer registry."""

from __future__ import annotations

from hydra_engine.command_output import reducers, shell
from hydra_engine.command_output.model import CommandOutput, CommandOutputReducer, Reduction
from hydra_engine.command_output.rendering import unknown_reduction

REDUCERS: tuple[CommandOutputReducer, ...] = (
    *reducers.dotnet.REDUCERS,
    *reducers.yarn.REDUCERS,
    *reducers.npm.REDUCERS,
    *reducers.docker.REDUCERS,
    *reducers.ripgrep.REDUCERS,
    *reducers.git.REDUCERS,
    *reducers.curl.REDUCERS,
)

REDUCERS_BY_NAME = {reducer.name: reducer for reducer in REDUCERS}


def reducer_for_command(command: str) -> CommandOutputReducer | None:
    parsed = shell.parse_command(command)
    for reducer in REDUCERS:
        if reducer.matches(parsed):
            return reducer
    return None


def reduce_command_output(command_output: CommandOutput, max_lines: int) -> Reduction:
    reducer = reducer_for_command(command_output.command)
    if reducer is None:
        return unknown_reduction(command_output)
    return reducer.reduce(command_output, max_lines)
