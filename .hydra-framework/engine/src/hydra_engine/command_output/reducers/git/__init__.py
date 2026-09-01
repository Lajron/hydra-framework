"""Git command-output reducers."""

from hydra_engine.command_output.reducers.git import diff, status

REDUCERS = (status.REDUCER, diff.REDUCER)

