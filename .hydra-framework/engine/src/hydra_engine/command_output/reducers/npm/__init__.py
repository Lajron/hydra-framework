"""Npm command-output reducers."""

from hydra_engine.command_output.reducers.npm import build, install, test

REDUCERS = (install.REDUCER, build.REDUCER, test.REDUCER)

