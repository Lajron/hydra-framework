"""Yarn command-output reducers."""

from hydra_engine.command_output.reducers.yarn import build, check_types, install, test

REDUCERS = (install.REDUCER, build.REDUCER, check_types.REDUCER, test.REDUCER)

