"""Inkling rule-based scoring engine.

Importing this module pulls in `inkling_engine.rules`, which in turn
imports each round module and self-registers its scorer with the runner.
This file stays round-agnostic — adding a new round means dropping a
module under `rules/` and listing it in `rules/__init__.py`.

The `llm` and `reveal` submodules attach the Phase 3 overreach +
reveal-layer support (Big Five overreach scorer, rule-based pricer,
rule-based targeter, stated-vs-revealed comparator). They are imported
for their side-effects (`llm/overreach.py` registers itself under the
"overreach" key for symmetry) but are invoked explicitly, never via
`/round-complete`.
"""
from inkling_engine import llm as _llm  # noqa: F401  (registers overreach shim)
from inkling_engine import reveal as _reveal  # noqa: F401
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
