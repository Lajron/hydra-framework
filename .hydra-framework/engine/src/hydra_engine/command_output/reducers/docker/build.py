"""Reducer for Docker build output."""

from __future__ import annotations

from hydra_engine.command_output.model import CommandOutput, CommandOutputReducer, ParsedCommand, Reduction
from hydra_engine.command_output.reducers import selection


def matches(parsed: ParsedCommand) -> bool:
    tokens = tuple(token.lower() for token in parsed.significant_tokens)
    return len(tokens) > 1 and parsed.head == "docker" and (tokens[1] == "build" or tokens[:3] == ("docker", "compose", "build"))


def reduce(command_output: CommandOutput, max_lines: int):
    return Reduction(**selection.reduction_fields(command_output, "docker-build", REDUCER.name, max_lines))


REDUCER = CommandOutputReducer("docker-build", "docker-build", selection.REDUCER_VERSION, matches, reduce)
