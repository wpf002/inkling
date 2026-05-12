"""Round 5 (Read) scorer.

Eight ambiguous social scenarios; each has four interpretation options
tagged on two axes:

  hostile | benign        — what kind of intent does the player infer?
  internal | external     — does the cause sit with the self or with circumstance?

Two inferences:

  A) attribution_style (high)   — aggregate scores on the two axes
  B) deliberation      (medium) — mean RT vs the round-internal first-half baseline

Citations:
  A) Weiner 1985; Crick & Dodge 1994 (attribution research)
  B) Krajbich et al. 2010 (drift-diffusion deliberation)
"""
from __future__ import annotations

from collections.abc import Iterable
from typing import Any

import numpy as np

from inkling_engine.models import Inference, RoundEventDTO
from inkling_engine.scoring.runner import register_scorer

CONFIDENCE_FLOOR = 0.05
DELIBERATION_CONFIDENCE_FLOOR = 0.7


def _index_trials(events: Iterable[RoundEventDTO]) -> list[dict[str, Any]]:
    rows: dict[str, dict[str, Any]] = {}
    sequence: list[str] = []
    for ev in events:
        p = ev.payload
        sid = p.get("scenario_id")
        if sid is None:
            continue
        sid = str(sid)
        rec = rows.setdefault(
            sid,
            {
                "scenario_id": sid,
                "selected_option_id": None,
                "tags": [],
                "rt_ms": None,
                "index": p.get("index"),
            },
        )
        if rec.get("index") is None and p.get("index") is not None:
            rec["index"] = p["index"]
        if ev.event_type == "scenario_shown":
            continue
        if ev.event_type == "option_selected":
            rec["selected_option_id"] = p.get("option_id")
            rec["rt_ms"] = p.get("rt_ms")
            tags = p.get("tags")
            if isinstance(tags, list):
                rec["tags"] = list(tags)
        if sid not in sequence:
            sequence.append(sid)
    return [rows[s] for s in sequence]


def _attribution_style(trials: list[dict[str, Any]]) -> Inference:
    answered = [t for t in trials if t.get("selected_option_id") is not None]
    n = len(answered)
    hostile = sum(1 for t in answered if "hostile" in (t.get("tags") or []))
    internal = sum(1 for t in answered if "internal" in (t.get("tags") or []))
    hostile_score = (hostile / n) if n else 0.0
    internal_score = (internal / n) if n else 0.0

    confidence = max(CONFIDENCE_FLOOR, min(1.0, n / 8.0))
    evidence: dict[str, Any] = {
        "scenarios_answered": n,
        "hostile_count": hostile,
        "internal_count": internal,
        "per_scenario": [
            {
                "scenario_id": t["scenario_id"],
                "option_id": t.get("selected_option_id"),
                "tags": t.get("tags"),
            }
            for t in answered
        ],
    }
    if n < 8:
        evidence["underpowered"] = True
    return Inference(
        construct="attribution_style",
        tier="high",
        value={"hostile_score": hostile_score, "internal_score": internal_score},
        confidence=confidence,
        evidence=evidence,
    )


def _deliberation(trials: list[dict[str, Any]]) -> Inference:
    rts = [
        (int(t.get("index") or 0), float(t["rt_ms"]))
        for t in trials
        if t.get("rt_ms") is not None
    ]
    rts.sort(key=lambda x: x[0])
    n = len(rts)
    if n == 0:
        return Inference(
            construct="deliberation",
            tier="medium",
            value={"mean_rt_ms": 0.0, "deliberation_index": 0.0},
            confidence=DELIBERATION_CONFIDENCE_FLOOR,
            evidence={"trials_used": 0, "underpowered": True},
        )

    values = [v for _, v in rts]
    mean_rt = float(np.mean(values))
    half = max(1, n // 2)
    first_half = [v for _, v in rts[:half]]
    second_half = [v for _, v in rts[half:]] or first_half
    baseline = float(np.mean(first_half))
    later_mean = float(np.mean(second_half))
    # Positive index = player slowed down (more deliberation) in the
    # second half relative to the first.
    deliberation_index = (later_mean - baseline) / baseline if baseline > 0 else 0.0

    # Within-subject baselines are noisy — confidence has a 0.7 floor.
    confidence = DELIBERATION_CONFIDENCE_FLOOR
    evidence: dict[str, Any] = {
        "trials_used": n,
        "first_half_mean": baseline,
        "second_half_mean": later_mean,
        "note": "within-subject baseline; confidence floored at 0.7",
    }
    return Inference(
        construct="deliberation",
        tier="medium",
        value={"mean_rt_ms": mean_rt, "deliberation_index": deliberation_index},
        confidence=confidence,
        evidence=evidence,
    )


def score_read(events: Iterable[RoundEventDTO]) -> list[Inference]:
    trials = _index_trials(events)
    return [_attribution_style(trials), _deliberation(trials)]


register_scorer("read", score_read)
