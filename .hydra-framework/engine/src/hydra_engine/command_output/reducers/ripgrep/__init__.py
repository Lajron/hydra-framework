"""Ripgrep command-output reducers."""

from hydra_engine.command_output.reducers.ripgrep import search

REDUCERS = (search.REDUCER,)

