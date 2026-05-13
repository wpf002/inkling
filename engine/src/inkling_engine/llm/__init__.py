"""LLM-backed Overreach scoring.

The overreach module is invoked explicitly from the reveal layer, not from
the round-complete pipeline. It is registered in the engine's scorer
registry under round_id="overreach" for symmetry, but the registered
adapter raises if called with a round-event stream — overreach takes a
session_summary dict, not events.
"""
from inkling_engine.llm.overreach import score_overreach  # noqa: F401

__all__ = ["score_overreach"]
