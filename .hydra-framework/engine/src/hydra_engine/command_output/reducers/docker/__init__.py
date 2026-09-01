"""Docker command-output reducers."""

from hydra_engine.command_output.reducers.docker import build, logs

REDUCERS = (build.REDUCER, logs.REDUCER)

