"""Engine tests for Round 6 (Dilemma) scoring."""
from __future__ import annotations

import json
from pathlib import Path

from inkling_engine import score_round

DILEMMAS_PATH = (
    Path(__file__).resolve().parents[2]
    / "content"
    / "rounds"
    / "dilemma"
    / "dilemmas.json"
)
DILEMMAS = json.loads(DILEMMAS_PATH.read_text())["dilemmas"]


def _events(picks: list[str], rts: list[int] | None = None) -> list[dict]:
    """picks[i] = "utilitarian" | "deontological" | "abandon"."""
    events: list[dict] = []
    t = 0
    rts = rts or [4000] * len(picks)
    for i, dilemma in enumerate(DILEMMAS[: len(picks)]):
        events.append(
            {
                "event_type": "dilemma_shown",
                "payload": {
                    "dilemma_id": dilemma["id"],
                    "type": dilemma["type"],
                    "hurried": dilemma["hurried"],
                },
                "t_ms": t,
            }
        )
        t += rts[i]
        pick = picks[i]
        if pick == "abandon":
            events.append(
                {
                    "event_type": "abandon",
                    "payload": {
                        "dilemma_id": dilemma["id"],
                        "type": dilemma["type"],
                        "hurried": dilemma["hurried"],
                    },
                    "t_ms": t,
                }
            )
        else:
            events.append(
                {
                    "event_type": "option_selected",
                    "payload": {
                        "dilemma_id": dilemma["id"],
                        "type": dilemma["type"],
                        "hurried": dilemma["hurried"],
                        "selected": pick,
                        "rt_ms": rts[i],
                    },
                    "t_ms": t,
                }
            )
        t += 200
    return events


def _by_construct(infs):
    return {i.construct: i for i in infs}


def test_typical_mixed_utilitarian():
    # 4 of 6 utilitarian.
    picks = ["utilitarian", "deontological", "deontological", "utilitarian",
             "utilitarian", "utilitarian"]
    infs = _by_construct(score_round("dilemma", _events(picks)))
    ul = infs["utilitarian_leaning"]
    assert abs(ul.value["utilitarian_rate"] - (4 / 6)) < 1e-9
    assert ul.confidence == 1.0
    sd = infs["personal_impersonal_sensitivity"]
    assert "sensitivity_delta" in sd.value


def test_extreme_full_utilitarian():
    picks = ["utilitarian"] * 6
    infs = _by_construct(score_round("dilemma", _events(picks)))
    ul = infs["utilitarian_leaning"]
    assert ul.value["utilitarian_rate"] == 1.0
    assert ul.value["personal_rate"] == 1.0
    assert ul.value["impersonal_rate"] == 1.0
    assert ul.confidence == 1.0
    sd = infs["personal_impersonal_sensitivity"]
    assert sd.value["sensitivity_delta"] == 0.0


def test_underpowered_two_decisions():
    picks = ["utilitarian", "deontological"]
    infs = _by_construct(score_round("dilemma", _events(picks)))
    ul = infs["utilitarian_leaning"]
    assert ul.evidence.get("underpowered") is True
    assert ul.confidence < 1.0
    sd = infs["personal_impersonal_sensitivity"]
    # With only one personal and one impersonal, sensitivity is computable
    # but still low-confidence.
    assert sd.confidence <= 0.6
