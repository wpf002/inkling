"""Inkling rule-based scoring engine.

Importing this module pulls in `inkling_engine.rules`, which in turn
imports each round module and self-registers its scorer with the runner.
This file stays round-agnostic — adding a new round means dropping a
module under `rules/` and listing it in `rules/__init__.py`.
"""
from inkling_engine import rules as _rules  # noqa: F401  (registers scorers)
from inkling_engine.models import Inference, RoundEventDTO
from inkling_engine.scoring.runner import (
    get_scorer,
    register_scorer,
    registered_rounds,
    score_round,
)

__all__ = [
    "Inference",
    "RoundEventDTO",
    "get_scorer",
    "register_scorer",
    "registered_rounds",
    "score_round",
]
