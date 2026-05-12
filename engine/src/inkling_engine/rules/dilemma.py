"""Round 6 (Dilemma) scorer.

Six moral dilemmas, each with a utilitarian and a deontological option.
Two inferences:

  A) utilitarian_leaning             (medium) — proportion of utilitarian choices
  B) personal_impersonal_sensitivity (medium) — utilitarian-rate diff
                                                between personal and impersonal

The utilitarian/deontological dichotomy is a simplification; current
literature (Kahane et al. 2018) flags that this contrast conflates
several distinct constructs. We report the proportion as a behavioral
summary, not a moral typology.

Citations:
  A) Greene et al. 2001 (fMRI of utilitarian vs deontological responses)
  B) Greene et al. 2004 (personal vs impersonal moral judgment)
"""
from __future__ import annotations

from collections.abc import Iterable
from typing import Any

from inkling_engine.models import Inference, RoundEventDTO
from inkling_engine.scoring.runner import register_scorer

CONFIDENCE_FLOOR = 0.05


def _index_trials(events: Iterable[RoundEventDTO]) -> list[dict[str, Any]]:
    rows: dict[str, dict[str, Any]] = {}
    sequence: list[str] = []
    for ev in events:
        p = ev.payload
        did = p.get("dilemma_id")
        if did is None:
            continue
        did = str(did)
        rec = rows.setdefault(
            did,
            {
                "dilemma_id": did,
                "type": p.get("type"),
                "hurried": p.get("hurried"),
                "selected": None,
                "abandoned": False,
                "rt_ms": None,
            },
        )
        for field in ("type", "hurried"):
            if rec.get(field) is None and p.get(field) is not None:
                rec[field] = p[field]
        if ev.event_type == "option_selected":
            rec["selected"] = p.get("selected")  # "utilitarian" | "deontological"
            rec["rt_ms"] = p.get("rt_ms")
        elif ev.event_type == "abandon":
            rec["abandoned"] = True
        if did not in sequence:
            sequence.append(did)
    return [rows[d] for d in sequence]


def _utilitarian_leaning(rows: list[dict[str, Any]]) -> Inference:
    valid = [r for r in rows if r.get("selected") in ("utilitarian", "deontological")]
    n = len(valid)
    util = sum(1 for r in valid if r["selected"] == "utilitarian")
    util_rate = util / n if n else 0.0

    personal = [r for r in valid if r.get("type") == "personal"]
    impersonal = [r for r in valid if r.get("type") == "impersonal"]
    personal_rate = (
        sum(1 for r in personal if r["selected"] == "utilitarian") / len(personal)
        if personal
        else 0.0
    )
    impersonal_rate = (
        sum(1 for r in impersonal if r["selected"] == "utilitarian") / len(impersonal)
        if impersonal
        else 0.0
    )

    confidence = max(CONFIDENCE_FLOOR, min(1.0, n / 6.0))
    evidence: dict[str, Any] = {
        "valid_choices": n,
        "utilitarian_count": util,
        "abandons": sum(1 for r in rows if r.get("abandoned")),
        "framing_note": "utilitarian/deontological is a simplification; see Kahane et al. 2018",
    }
    if n < 6:
        evidence["underpowered"] = True
    return Inference(
        construct="utilitarian_leaning",
        tier="medium",
        value={
            "utilitarian_rate": util_rate,
            "personal_rate": personal_rate,
            "impersonal_rate": impersonal_rate,
        },
        confidence=confidence,
        evidence=evidence,
    )


def _personal_impersonal_sensitivity(rows: list[dict[str, Any]]) -> Inference:
    valid = [r for r in rows if r.get("selected") in ("utilitarian", "deontological")]
    personal = [r for r in valid if r.get("type") == "personal"]
    impersonal = [r for r in valid if r.get("type") == "impersonal"]
    if not personal or not impersonal:
        return Inference(
            construct="personal_impersonal_sensitivity",
            tier="medium",
            value={"sensitivity_delta": 0.0},
            confidence=CONFIDENCE_FLOOR,
            evidence={
                "personal_trials": len(personal),
                "impersonal_trials": len(impersonal),
                "underpowered": True,
            },
        )
    util_personal = sum(1 for r in personal if r["selected"] == "utilitarian") / len(personal)
    util_impersonal = (
        sum(1 for r in impersonal if r["selected"] == "utilitarian") / len(impersonal)
    )
    delta = util_impersonal - util_personal

    n_min = min(len(personal), len(impersonal))
    confidence = max(CONFIDENCE_FLOOR, min(1.0, n_min / 2.0))
    return Inference(
        construct="personal_impersonal_sensitivity",
        tier="medium",
        value={"sensitivity_delta": delta},
        confidence=confidence,
        evidence={
            "personal_trials": len(personal),
            "impersonal_trials": len(impersonal),
            "util_personal_rate": util_personal,
            "util_impersonal_rate": util_impersonal,
        },
    )


def score_dilemma(events: Iterable[RoundEventDTO]) -> list[Inference]:
    rows = _index_trials(events)
    return [
        _utilitarian_leaning(rows),
        _personal_impersonal_sensitivity(rows),
    ]


register_scorer("dilemma", score_dilemma)
