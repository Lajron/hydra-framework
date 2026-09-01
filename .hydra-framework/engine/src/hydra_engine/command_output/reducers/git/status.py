"""Reducer for `git status` output."""

from __future__ import annotations

from hydra_engine.command_output import shell
from hydra_engine.command_output.model import CommandOutput, CommandOutputReducer, ParsedCommand, Reduction
from hydra_engine.command_output.reducers import selection


def matches(parsed: ParsedCommand) -> bool:
    return parsed.head == "git" and shell.git_subcommand(parsed.significant_tokens) == "status"


def reduce(command_output: CommandOutput, max_lines: int):
    return Reduction(**selection.reduction_fields(command_output, "git-status", REDUCER.name, max_lines))


REDUCER = CommandOutputReducer("git-status", "git-status", selection.REDUCER_VERSION, matches, reduce)
