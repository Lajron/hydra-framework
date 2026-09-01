"""Dotnet command-output reducers."""

from hydra_engine.command_output.reducers.dotnet import build, restore, test

REDUCERS = (build.REDUCER, test.REDUCER, restore.REDUCER)

