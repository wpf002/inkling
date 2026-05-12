"""Round 4 (Memory) scorer.

Corsi block-tapping. Sequences light up and the player taps them back.
Span grows on success, two trials per span, stop after two failures at
the same span.

Inferences:
  A) working_memory_span    (high)   — max span with >=1 correct trial
  B) processing_speed       (high)   — mean tap RT, normalized by span
  C) performance_under_load (medium) — accuracy drop from start span to
                                       start_span + 3

Citations:
  A) Corsi 1972; Kessels et al. 2000
  B) standard psychophysics
  C) Baddeley & Hitch 1974
"""
from __future__ import annotations

from collections.abc import Iterable
from typing import Any

import numpy as np

from inkling_engine.models import Inference, RoundEventDTO
from inkling_engine.scoring.runner import register_scorer

CONFIDENCE_FLOOR = 0.05


def _index_trials(events: Iterable[RoundEventDTO]) -> tuple[int, list[dict[str, Any]]]:
    start_span = 3
    by_trial: dict[str, dict[str, Any]] = {}
    for ev in events:
        if ev.event_type == "round_start":
            start_span = int(ev.payload.get("start_span") or start_span)
            continue
        p = ev.payload
        tid = p.get("trial_id")
        if tid is None:
            continue
        tid = str(tid)
        rec = by_trial.setdefault(
            tid,
            {
                "trial_id": tid,
                "span": p.get("span"),
                "correct": None,
                "tap_rts_ms": [],
            },
        )
        if rec.get("span") is None and p.get("span") is not None:
            rec["span"] = p["span"]
        if ev.event_type == "sequence_shown":
            continue
        if ev.event_type == "response":
            rec["correct"] = bool(p.get("correct"))
            tap_rts = p.get("tap_rts_ms")
            if isinstance(tap_rts, list):
                rec["tap_rts_ms"] = [float(x) for x in tap_rts if isinstance(x, int | float)]
    return start_span, list(by_trial.values())


def _working_memory_span(trials: list[dict[str, Any]]) -> Inference:
    spans_correct = sorted(
        {int(t["span"]) for t in trials if t.get("correct") and t.get("span") is not None}
    )
    max_span = spans_correct[-1] if spans_correct else 0
    n_correct = sum(1 for t in trials if t.get("correct"))
    n_attempted = sum(1 for t in trials if t.get("correct") is not None)
    evidence: dict[str, Any] = {
        "total_correct": n_correct,
        "total_attempted": n_attempted,
        "spans_with_correct": spans_correct,
    }
    confidence = 1.0 if n_attempted >= 4 else max(CONFIDENCE_FLOOR, n_attempted / 4.0)
    if n_attempted < 4:
        evidence["underpowered"] = True
    return Inference(
        construct="working_memory_span",
        tier="high",
        value={
            "span": max_span,
            "total_correct": n_correct,
            "total_attempted": n_attempted,
        },
        confidence=confidence,
        evidence=evidence,
    )


def _processing_speed(trials: list[dict[str, Any]]) -> Inference:
    rts_per_span: list[tuple[int, float]] = []
    all_rts: list[float] = []
    for t in trials:
        span = t.get("span")
        rts = t.get("tap_rts_ms") or []
        if span is None or not rts:
            continue
        for rt in rts:
            rts_per_span.append((int(span), float(rt)))
            all_rts.append(float(rt))

    if not all_rts:
        return Inference(
            construct="processing_speed",
            tier="high",
            value={"mean_tap_rt_ms": 0.0, "normalized_speed": 0.0},
            confidence=CONFIDENCE_FLOOR,
            evidence={"trials_used": 0, "underpowered": True},
        )

    mean_rt = float(np.mean(all_rts))
    # Normalized speed: 1 / (mean RT in seconds), divided by span median
    # so larger spans aren't unfairly penalized.
    median_span = float(np.median([s for s, _ in rts_per_span])) or 1.0
    normalized = (1000.0 / mean_rt) * median_span if mean_rt > 0 else 0.0

    trials_with_rts = sum(1 for t in trials if t.get("tap_rts_ms"))
    confidence = max(CONFIDENCE_FLOOR, min(1.0, trials_with_rts / 6.0))
    evidence: dict[str, Any] = {
        "trials_used": trials_with_rts,
        "total_taps": len(all_rts),
        "median_span_observed": median_span,
    }
    if trials_with_rts < 6:
        evidence["underpowered"] = True
    return Inference(
        construct="processing_speed",
        tier="high",
        value={"mean_tap_rt_ms": mean_rt, "normalized_speed": normalized},
        confidence=confidence,
        evidence=evidence,
    )


def _performance_under_load(start_span: int, trials: list[dict[str, Any]]) -> Inference:
    high_span = start_span + 3
    low = [t for t in trials if t.get("span") == start_span and t.get("correct") is not None]
    high = [t for t in trials if t.get("span") == high_span and t.get("correct") is not None]

    def acc(rows: list[dict[str, Any]]) -> float:
        if not rows:
            return 0.0
        return sum(1 for r in rows if r.get("correct")) / len(rows)

    acc_low = acc(low)
    acc_high = acc(high)
    drop = acc_low - acc_high

    n_min = min(len(low), len(high))
    if n_min == 0:
        confidence = CONFIDENCE_FLOOR
    else:
        confidence = max(CONFIDENCE_FLOOR, min(1.0, n_min / 2.0))

    evidence: dict[str, Any] = {
        "start_span": start_span,
        "high_span": high_span,
        "trials_at_low_span": len(low),
        "trials_at_high_span": len(high),
    }
    if n_min == 0:
        evidence["high_span_not_reached"] = True
        evidence["underpowered"] = True

    return Inference(
        construct="performance_under_load",
        tier="medium",
        value={
            "accuracy_at_low_span": acc_low,
            "accuracy_at_high_span": acc_high,
            "drop": drop,
        },
        confidence=confidence,
        evidence=evidence,
    )


def score_memory(events: Iterable[RoundEventDTO]) -> list[Inference]:
    start_span, trials = _index_trials(events)
    return [
        _working_memory_span(trials),
        _processing_speed(trials),
        _performance_under_load(start_span, trials),
    ]


register_scorer("memory", score_memory)
