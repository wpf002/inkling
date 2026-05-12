"""Round-agnostic scorer registry and dispatch."""
from collections.abc import Callable, Iterable
from typing import Any

from inkling_engine.models import Inference, RoundEventDTO

ScorerFn = Callable[[Iterable[RoundEventDTO]], list[Inference]]
_REGISTRY: dict[str, ScorerFn] = {}


def register_scorer(round_id: str, fn: ScorerFn) -> None:
    _REGISTRY[round_id] = fn


def get_scorer(round_id: str) -> ScorerFn | None:
    return _REGISTRY.get(round_id)


def registered_rounds() -> list[str]:
    return list(_REGISTRY.keys())


def score_round(round_id: str, events: Iterable[Any]) -> list[Inference]:
    fn = _REGISTRY.get(round_id)
    if fn is None:
        raise KeyError(f"no scorer registered for round_id={round_id!r}")
    dtos = [e if isinstance(e, RoundEventDTO) else RoundEventDTO.model_validate(e) for e in events]
    return fn(dtos)
