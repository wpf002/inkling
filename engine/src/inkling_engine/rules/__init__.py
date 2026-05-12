"""Per-round scoring rules.

Each round module owns its own registration call (at the bottom of the
module). Adding a new round means adding a new `rules/<round>.py` and
listing it here so the import side-effect runs.
"""
from inkling_engine.rules import (  # noqa: F401
    choice,
    dilemma,
    memory,
    pursuit,
    read,
    trust,
)

__all__ = ["choice", "dilemma", "memory", "pursuit", "read", "trust"]
