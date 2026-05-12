"""Round 3 (Trust) scorer.

Iterated Trust Game with four partner personas, each seen twice. Three
inferences emitted:

  A) initial_trust_propensity (high)   — mean first-trial send across NPCs
  B) adaptation_rate          (medium) — correlation of received-N with sent-(N+1)
  C) retaliation_tendency     (medium) — send-amount drop after a low return

The scorer is stateless and round-agnostic in shape. It reads `send_amount`
and `outcome_revealed` events keyed by `trial_id` / `npc_id`. The persona
labels themselves never leak into the value structure — only an aggregated
"selfish-return" flag from the received fraction.

Citations:
  A) Berg, Dickhaut & McCabe 1995
  B) King-Casas et al. 2005
  C) Fehr & Gächter 2000
"""
from __future__ import annotations

from collections.abc import Iterable
from typing import Any

import numpy as np

from inkling_engine.models import Inference, RoundEventDTO
from inkling_engine.scoring.runner import register_scorer

CONFIDENCE_FLOOR = 0.05
SELFISH_RETURN_FRACTION = 0.20  # received/sent below this is "selfish"


def _index_trials(events: Iterable[RoundEventDTO]) -> list[dict[str, Any]]:
    rows: dict[str, dict[str, Any]] = {}
    sequence: list[str] = []
    for ev in events:
        p = ev.payload
        tid = p.get("trial_id")
        if tid is None:
            continue
        tid = str(tid)
        rec = rows.setdefault(
            tid,
            {
                "trial_id": tid,
                "npc_id": p.get("npc_id"),
                "first": p.get("first"),
                "send_amount": None,
                "received_amount": None,
                "t_ms": ev.t_ms,
            },
        )
        if tid not in sequence:
            sequence.append(tid)
        for field in ("npc_id", "first"):
            if rec.get(field) is None and p.get(field) is not None:
                rec[field] = p[field]
        if ev.event_type == "send_amount":
            rec["send_amount"] = p.get("amount")
            rec["t_ms"] = ev.t_ms
        elif ev.event_type == "outcome_revealed":
            rec["received_amount"] = p.get("received")
    return [rows[t] for t in sequence]


def _initial_trust(rows: list[dict[str, Any]]) -> Inference:
    first_rows = [r for r in rows if r.get("first") and r.get("send_amount") is not None]
    n = len(first_rows)
    if n == 0:
        return Inference(
            construct="initial_trust_propensity",
            tier="high",
            value={"initial_trust_amount": 0.0, "sd": 0.0},
            confidence=CONFIDENCE_FLOOR,
            evidence={"npcs_with_first_trial": 0, "underpowered": True},
        )

    amts = np.array([float(r["send_amount"]) for r in first_rows])
    mean = float(np.mean(amts))
    sd = float(np.std(amts, ddof=0))
    confidence = 1.0 if n >= 4 else max(CONFIDENCE_FLOOR, n / 4.0)
    evidence: dict[str, Any] = {
        "npcs_with_first_trial": n,
        "per_npc_first_send": {r["npc_id"]: r["send_amount"] for r in first_rows},
    }
    if n < 4:
        evidence["underpowered"] = True
    return Inference(
        construct="initial_trust_propensity",
        tier="high",
        value={"initial_trust_amount": mean, "sd": sd},
        confidence=confidence,
        evidence=evidence,
    )


def _adaptation_rate(rows: list[dict[str, Any]]) -> Inference:
    # Pair (N, N+1) by npc: received on N → sent on N+1.
    by_npc: dict[str, list[dict[str, Any]]] = {}
    for r in rows:
        npc = r.get("npc_id")
        if npc is None:
            continue
        by_npc.setdefault(str(npc), []).append(r)

    received: list[float] = []
    next_sent: list[float] = []
    pairs: list[dict[str, Any]] = []
    for npc, seq in by_npc.items():
        seq_sorted = sorted(seq, key=lambda r: r.get("t_ms", 0))
        for i in range(len(seq_sorted) - 1):
            a = seq_sorted[i]
            b = seq_sorted[i + 1]
            if a.get("received_amount") is None or b.get("send_amount") is None:
                continue
            received.append(float(a["received_amount"]))
            next_sent.append(float(b["send_amount"]))
            pairs.append(
                {
                    "npc_id": npc,
                    "received_on_n": a["received_amount"],
                    "sent_on_n_plus_1": b["send_amount"],
                }
            )

    n_pairs = len(received)
    if n_pairs < 2 or float(np.std(received)) == 0.0 or float(np.std(next_sent)) == 0.0:
        return Inference(
            construct="adaptation_rate",
            tier="medium",
            value={"adaptation_correlation": 0.0, "n_pairs": n_pairs},
            confidence=CONFIDENCE_FLOOR,
            evidence={"pairs": pairs, "underpowered": True},
        )

    corr = float(np.corrcoef(received, next_sent)[0, 1])
    confidence = max(CONFIDENCE_FLOOR, min(1.0, n_pairs / 4.0))
    return Inference(
        construct="adaptation_rate",
        tier="medium",
        value={"adaptation_correlation": corr, "n_pairs": n_pairs},
        confidence=confidence,
        evidence={"pairs": pairs},
    )


def _retaliation_tendency(rows: list[dict[str, Any]]) -> Inference:
    by_npc: dict[str, list[dict[str, Any]]] = {}
    for r in rows:
        npc = r.get("npc_id")
        if npc is None:
            continue
        by_npc.setdefault(str(npc), []).append(r)

    drops: list[float] = []
    per_npc: list[dict[str, Any]] = []
    recovery_lengths: list[int] = []
    all_sends: list[float] = []
    for r in rows:
        if r.get("send_amount") is not None:
            all_sends.append(float(r["send_amount"]))
    baseline = float(np.mean(all_sends)) if all_sends else 0.0

    for npc, seq in by_npc.items():
        seq_sorted = sorted(seq, key=lambda r: r.get("t_ms", 0))
        for i in range(len(seq_sorted) - 1):
            a = seq_sorted[i]
            b = seq_sorted[i + 1]
            sent_a = a.get("send_amount")
            recv_a = a.get("received_amount")
            sent_b = b.get("send_amount")
            if sent_a is None or recv_a is None or sent_b is None or float(sent_a) == 0.0:
                continue
            recv_frac = float(recv_a) / (float(sent_a) * 3.0)
            if recv_frac < SELFISH_RETURN_FRACTION:
                drop = float(sent_b) - baseline
                drops.append(drop)
                recovery_lengths.append(1)
                per_npc.append(
                    {
                        "npc_id": npc,
                        "selfish_received_frac": recv_frac,
                        "next_send_vs_baseline": drop,
                    }
                )

    retaliation_delta = float(np.mean(drops)) if drops else 0.0
    n = len(drops)
    if n == 0:
        confidence = CONFIDENCE_FLOOR
    else:
        signs = [1 if d < 0 else (-1 if d > 0 else 0) for d in drops]
        directional = abs(sum(signs)) / len(signs)
        confidence = max(CONFIDENCE_FLOOR, min(1.0, directional * 0.7 + 0.2))

    evidence: dict[str, Any] = {
        "events_observed": n,
        "baseline_send": baseline,
        "per_event": per_npc,
    }
    if n == 0:
        evidence["underpowered"] = True

    return Inference(
        construct="retaliation_tendency",
        tier="medium",
        value={
            "retaliation_delta": retaliation_delta,
            "recovery_trials": int(np.mean(recovery_lengths)) if recovery_lengths else 0,
        },
        confidence=confidence,
        evidence=evidence,
    )


def score_trust(events: Iterable[RoundEventDTO]) -> list[Inference]:
    rows = _index_trials(events)
    return [
        _initial_trust(rows),
        _adaptation_rate(rows),
        _retaliation_tendency(rows),
    ]


register_scorer("trust", score_trust)
