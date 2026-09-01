"""Reducer for `git diff` output."""

from __future__ import annotations

from hydra_engine.command_output import shell
from hydra_engine.command_output.model import CommandOutput, CommandOutputReducer, ParsedCommand, Reduction
from hydra_engine.command_output.reducers import selection


def matches(parsed: ParsedCommand) -> bool:
    return parsed.head == "git" and shell.git_subcommand(parsed.significant_tokens) == "diff"


def reduce(command_output: CommandOutput, max_lines: int):
    return Reduction(**selection.reduction_fields(command_output, "git-diff", REDUCER.name, max_lines))


REDUCER = CommandOutputReducer("git-diff", "git-diff", selection.REDUCER_VERSION, matches, reduce)
