"""Round-agnostic helpers for scorers."""
from collections.abc import Iterable
from math import exp, log
from typing import Any

from inkling_engine.models import RoundEventDTO


def sigmoid(x: float) -> float:
    if x >= 0:
        z = exp(-x)
        return 1.0 / (1.0 + z)
    z = exp(x)
    return z / (1.0 + z)


def safe_log(p: float, eps: float = 1e-12) -> float:
    return log(max(min(p, 1.0 - eps), eps))


def to_dtos(events: Iterable[Any]) -> list[RoundEventDTO]:
    out: list[RoundEventDTO] = []
    for e in events:
        if isinstance(e, RoundEventDTO):
            out.append(e)
        else:
            out.append(RoundEventDTO.model_validate(e))
    return out


def trials_from_events(events: Iterable[Any]) -> dict[str, dict[str, Any]]:
    """Index a stream of round events into per-trial dicts.

    A trial key is `{condition}:{gamble_id}`. Each entry collapses the
    matching `gamble_shown`, `choice`, and `abandon` events into a single
    record. Round-agnostic: only looks at well-known event types and the
    `trial`, `gamble_id`, `condition`, `value`, `rt_ms` fields in payloads.
    """
    by_trial: dict[str, dict[str, Any]] = {}
    for ev in to_dtos(events):
        p = ev.payload
        trial_key = p.get("trial")
        if trial_key is None:
            continue
        rec = by_trial.setdefault(
            str(trial_key),
            {
                "trial": str(trial_key),
                "gamble_id": p.get("gamble_id"),
                "condition": p.get("condition"),
                "win": p.get("win"),
                "lose": p.get("lose"),
                "choice": None,
                "rt_ms": None,
                "abandoned": False,
            },
        )
        for field in ("gamble_id", "condition", "win", "lose"):
            if rec.get(field) is None and p.get(field) is not None:
                rec[field] = p[field]

        if ev.event_type == "choice":
            rec["choice"] = p.get("value")
            rec["rt_ms"] = p.get("rt_ms")
        elif ev.event_type == "abandon":
            rec["abandoned"] = True
            if rec["rt_ms"] is None:
                rec["rt_ms"] = p.get("rt_ms")
    return by_trial
