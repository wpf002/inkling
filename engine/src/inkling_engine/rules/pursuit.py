"""Round 2 (Pursuit) scorer.

Four inferences derived from a stream of trial_shown + click | miss
events:

  A) reaction_time_profile (high)   — median, CV, p10, p90 of RTs on hits
  B) sustained_attention   (high)   — RT slope across the round
  C) frustration_tolerance (medium) — post-spike RT and miss-rate delta
  D) response_inhibition   (medium) — false-alarm rate on distractor frames

The scorer is stateless: it consumes an iterable of RoundEventDTO and
returns a list[Inference]. Trial indexing is derived from
`payload.trial` keys; the scorer never assumes a specific round id.

Citations:
  A) standard psychophysics
  B) Mackworth 1948 (vigilance decrement)
  C) Rosenzweig 1944 (frustration-aggression literature)
  D) Logan & Cowan 1984 (response inhibition)
"""
from __future__ import annotations

from collections.abc import Iterable
from typing import Any

import numpy as np

from inkling_engine.models import Inference, RoundEventDTO
from inkling_engine.scoring.runner import register_scorer

CONFIDENCE_FLOOR = 0.05


def _index_trials(events: Iterable[RoundEventDTO]) -> dict[str, dict[str, Any]]:
    by_trial: dict[str, dict[str, Any]] = {}
    spike_indices: list[int] = []
    for ev in events:
        if ev.event_type == "round_start":
            spikes = ev.payload.get("spike_indices") or []
            if isinstance(spikes, list):
                spike_indices = [int(i) for i in spikes]
            continue
        p = ev.payload
        tid = p.get("trial")
        if tid is None:
            continue
        rec = by_trial.setdefault(
            str(tid),
            {
                "trial": str(tid),
                "index": p.get("index"),
                "target_type": p.get("target_type"),
                "window_ms": p.get("window_ms"),
                "rt_ms": None,
                "outcome": None,
            },
        )
        for field in ("index", "target_type", "window_ms"):
            if rec.get(field) is None and p.get(field) is not None:
                rec[field] = p[field]
        if ev.event_type == "trial_shown":
            continue
        if ev.event_type == "click":
            rec["outcome"] = "click"
            rec["rt_ms"] = p.get("rt_ms")
        elif ev.event_type == "miss":
            rec["outcome"] = "miss"
            rec["rt_ms"] = p.get("rt_ms")
    # Annotate spikes on each trial so downstream code does not need the
    # round_start event again.
    for r in by_trial.values():
        idx = r.get("index")
        r["is_spike"] = idx is not None and int(idx) in spike_indices
    return by_trial


def _hit_rts(trials: list[dict[str, Any]]) -> list[float]:
    return [
        float(t["rt_ms"])
        for t in trials
        if t.get("target_type") == "valid"
        and t.get("outcome") == "click"
        and t.get("rt_ms") is not None
    ]


def _reaction_time_profile(trials: list[dict[str, Any]]) -> Inference:
    rts = _hit_rts(trials)
    n = len(rts)
    if n == 0:
        return Inference(
            construct="reaction_time_profile",
            tier="high",
            value={"median_rt_ms": 0.0, "coefficient_of_variation": 0.0, "p10_rt_ms": 0.0, "p90_rt_ms": 0.0},
            confidence=CONFIDENCE_FLOOR,
            evidence={"trials_used": 0, "underpowered": True, "per_quartile_medians": []},
        )

    arr = np.array(rts)
    median = float(np.median(arr))
    mean = float(np.mean(arr))
    sd = float(np.std(arr, ddof=0))
    cv = sd / mean if mean > 0 else 0.0
    p10 = float(np.percentile(arr, 10))
    p90 = float(np.percentile(arr, 90))

    # Per-quartile medians (split rts by trial index quartile to keep
    # this round-agnostic, not by time).
    valids_sorted = sorted(
        (t for t in trials if t.get("target_type") == "valid" and t.get("outcome") == "click"),
        key=lambda t: (t.get("index") if t.get("index") is not None else 0),
    )
    per_quartile: list[float] = []
    if valids_sorted:
        chunks = np.array_split(np.array([float(t["rt_ms"]) for t in valids_sorted]), 4)
        per_quartile = [float(np.median(c)) if len(c) else 0.0 for c in chunks]

    confidence = min(1.0, n / 20.0)
    underpowered = n < 20

    evidence: dict[str, Any] = {
        "trials_used": n,
        "per_quartile_medians": per_quartile,
    }
    if underpowered:
        evidence["underpowered"] = True

    return Inference(
        construct="reaction_time_profile",
        tier="high",
        value={
            "median_rt_ms": median,
            "coefficient_of_variation": cv,
            "p10_rt_ms": p10,
            "p90_rt_ms": p90,
        },
        confidence=confidence,
        evidence=evidence,
    )


def _sustained_attention(trials: list[dict[str, Any]]) -> Inference:
    hits = sorted(
        (
            t
            for t in trials
            if t.get("target_type") == "valid"
            and t.get("outcome") == "click"
            and t.get("rt_ms") is not None
            and t.get("index") is not None
        ),
        key=lambda t: int(t["index"]),
    )
    n = len(hits)
    if n < 4:
        return Inference(
            construct="sustained_attention",
            tier="high",
            value={
                "rt_slope_ms_per_trial": 0.0,
                "first_half_median": 0.0,
                "second_half_median": 0.0,
            },
            confidence=CONFIDENCE_FLOOR,
            evidence={"trials_used": n, "underpowered": True},
        )

    xs = np.array([int(t["index"]) for t in hits], dtype=float)
    ys = np.array([float(t["rt_ms"]) for t in hits])
    slope, intercept = np.polyfit(xs, ys, 1)
    y_hat = slope * xs + intercept
    ss_res = float(np.sum((ys - y_hat) ** 2))
    ss_tot = float(np.sum((ys - ys.mean()) ** 2)) or 1e-12
    r_squared = max(0.0, 1.0 - ss_res / ss_tot)

    mid = n // 2
    first_half = ys[:mid] if mid > 0 else ys
    second_half = ys[mid:] if mid > 0 else ys
    first_med = float(np.median(first_half))
    second_med = float(np.median(second_half))

    confidence = max(CONFIDENCE_FLOOR, min(1.0, r_squared))

    return Inference(
        construct="sustained_attention",
        tier="high",
        value={
            "rt_slope_ms_per_trial": float(slope),
            "first_half_median": first_med,
            "second_half_median": second_med,
        },
        confidence=confidence,
        evidence={"trials_used": n, "r_squared": r_squared},
    )


def _frustration_tolerance(trials: list[dict[str, Any]]) -> Inference:
    indexed = {int(t["index"]): t for t in trials if t.get("index") is not None}
    spike_trials = [t for t in indexed.values() if t.get("is_spike")]
    deltas_rt: list[float] = []
    deltas_miss: list[float] = []
    per_spike: list[dict[str, Any]] = []

    for st in spike_trials:
        idx = int(st["index"])
        pre = [indexed.get(idx - k) for k in (1, 2, 3)]
        post = [indexed.get(idx + k) for k in (1, 2, 3)]
        pre = [t for t in pre if t and t.get("target_type") == "valid"]
        post = [t for t in post if t and t.get("target_type") == "valid"]
        if not pre or not post:
            continue
        pre_rts = [float(t["rt_ms"]) for t in pre if t.get("outcome") == "click" and t.get("rt_ms") is not None]
        post_rts = [float(t["rt_ms"]) for t in post if t.get("outcome") == "click" and t.get("rt_ms") is not None]
        if pre_rts and post_rts:
            rt_d = float(np.mean(post_rts) - np.mean(pre_rts))
            deltas_rt.append(rt_d)
        else:
            rt_d = None
        pre_miss = sum(1 for t in pre if t.get("outcome") == "miss") / len(pre)
        post_miss = sum(1 for t in post if t.get("outcome") == "miss") / len(post)
        deltas_miss.append(post_miss - pre_miss)
        per_spike.append(
            {
                "spike_index": idx,
                "rt_delta_ms": rt_d,
                "miss_rate_delta": post_miss - pre_miss,
            }
        )

    rt_delta = float(np.mean(deltas_rt)) if deltas_rt else 0.0
    miss_delta = float(np.mean(deltas_miss)) if deltas_miss else 0.0

    if deltas_rt:
        signs = [1 if d > 0 else (-1 if d < 0 else 0) for d in deltas_rt]
        directional = abs(sum(signs)) / len(signs)
    else:
        directional = 0.0
    confidence = max(CONFIDENCE_FLOOR, min(1.0, directional * 0.7 + 0.2))

    evidence: dict[str, Any] = {"per_spike": per_spike, "spikes_used": len(per_spike)}
    if len(per_spike) < 3:
        evidence["underpowered"] = True

    return Inference(
        construct="frustration_tolerance",
        tier="medium",
        value={
            "post_spike_rt_delta_ms": rt_delta,
            "post_spike_miss_rate_delta": miss_delta,
        },
        confidence=confidence,
        evidence=evidence,
    )


def _response_inhibition(trials: list[dict[str, Any]]) -> Inference:
    distractors = [t for t in trials if t.get("target_type") == "distractor"]
    valids = [t for t in trials if t.get("target_type") == "valid"]
    n_dist = len(distractors)
    n_valid = len(valids)
    false_alarms = sum(1 for t in distractors if t.get("outcome") == "click")
    hits = sum(1 for t in valids if t.get("outcome") == "click")
    fa_rate = false_alarms / n_dist if n_dist else 0.0
    hit_rate = hits / n_valid if n_valid else 0.0

    total = n_dist + n_valid
    confidence = max(CONFIDENCE_FLOOR, min(1.0, total / 30.0))

    evidence: dict[str, Any] = {
        "trials_used": total,
        "distractor_trials": n_dist,
        "valid_trials": n_valid,
        "false_alarms": false_alarms,
        "hits": hits,
    }
    if n_dist == 0:
        evidence["underpowered"] = True

    return Inference(
        construct="response_inhibition",
        tier="medium",
        value={"false_alarm_rate": fa_rate, "hit_rate": hit_rate},
        confidence=confidence,
        evidence=evidence,
    )


def score_pursuit(events: Iterable[RoundEventDTO]) -> list[Inference]:
    by_trial = _index_trials(events)
    trials = list(by_trial.values())
    return [
        _reaction_time_profile(trials),
        _sustained_attention(trials),
        _frustration_tolerance(trials),
        _response_inhibition(trials),
    ]


register_scorer("pursuit", score_pursuit)
