"""Executor registry — kind -> callable(spec) -> result dict, raises on failure.

Add a new job kind by writing executors/<kind>.py with a run(spec) function and
registering it here. Keep it that boring: runner.py doesn't know or care what a
kind actually does, only that it takes a spec and returns/raises.
"""
from . import research

EXECUTORS = {
    "research": research.run,
}
