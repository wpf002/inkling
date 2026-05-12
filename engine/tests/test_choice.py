"""Engine tests for Round 1 (Choice) scoring.

The fixture `events_from_trials` builds a synthetic event stream from
(gamble_id, condition, choice, reaction_time_ms) tuples — `choice` may be
"take", "decline", or "abandon". Gamble win/lose values come from
content/rounds/choice/gambles.json so the tests stay aligned with the
authored content.
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from inkling_engine import score_round

GAMBLES_PATH = (
    Path(__file__).resolve().parents[2]
    / "content"
    / "rounds"
    / "choice"
    / "gambles.json"
)
GAMBLES = {g["id"]: g for g in json.loads(GAMBLES_PATH.read_text())["gambles"]}


def _events(trials: list[tuple[str, str, str, int]]) -> list[dict]:
    out: list[dict] = []
    t = 0
    for i, (gid, cond, choice, rt) in enumerate(trials):
        g = GAMBLES[gid]
        trial_key = f"{cond}:{gid}"
        out.append(
            {
                "event_type": "gamble_shown",
                "payload": {
                    "trial": trial_key,
                    "gamble_id": gid,
                    "condition": cond,
                    "win": g["win"],
                    "lose": g["lose"],
                },
                "t_ms": t,
            }
        )
        t += rt
        if choice == "abandon":
            out.append(
                {
                    "event_type": "abandon",
                    "payload": {
                        "trial": trial_key,
                        "gamble_id": gid,
                        "condition": cond,
                        "rt_ms": rt,
                    },
                    "t_ms": t,
                }
            )
        else:
            out.append(
                {
                    "event_type": "choice",
                    "payload": {
                        "trial": trial_key,
                        "gamble_id": gid,
                        "condition": cond,
                        "value": choice,
                        "rt_ms": rt,
                    },
                    "t_ms": t,
                }
            )
        t += 50 + i  # spacing
    return out


def _by_construct(infs):
    return {i.construct: i for i in infs}


# --- loss aversion ---------------------------------------------------------


def test_lambda_low_ratio_player():
    trials = [
        ("g1", "unhurried", "decline", 1500),
        ("g2", "unhurried", "take", 1200),
        ("g3", "unhurried", "take", 1100),
        ("g4", "unhurried", "take", 1000),
        ("g1", "hurried", "decline", 900),
        ("g2", "hurried", "take", 800),
        ("g3", "hurried", "take", 700),
        ("g4", "hurried", "take", 700),
    ]
    infs = _by_construct(score_round("choice", _events(trials)))
    la = infs["loss_aversion"]
    assert 0.95 <= la.value["lambda"] <= 1.85, la.value
    assert la.confidence >= 0.5


def test_lambda_population_mean_player():
    trials = [
        ("g1", "unhurried", "decline", 1500),
        ("g2", "unhurried", "decline", 1400),
        ("g3", "unhurried", "take", 1100),
        ("g4", "unhurried", "take", 1000),
        ("g1", "hurried", "decline", 900),
        ("g2", "hurried", "decline", 800),
        ("g3", "hurried", "take", 700),
        ("g4", "hurried", "take", 700),
    ]
    infs = _by_construct(score_round("choice", _events(trials)))
    la = infs["loss_aversion"]
    assert 1.75 <= la.value["lambda"] <= 2.45, la.value
    assert la.confidence >= 0.5


def test_lambda_high_ratio_player():
    trials = [
        ("g1", "unhurried", "decline", 1500),
        ("g2", "unhurried", "decline", 1400),
        ("g3", "unhurried", "decline", 1300),
        ("g4", "unhurried", "take", 1000),
        ("g1", "hurried", "decline", 900),
        ("g2", "hurried", "decline", 800),
        ("g3", "hurried", "decline", 700),
        ("g4", "hurried", "take", 700),
    ]
    infs = _by_construct(score_round("choice", _events(trials)))
    la = infs["loss_aversion"]
    assert 2.5 <= la.value["lambda"] <= 5.0, la.value
    assert la.confidence >= 0.3


def test_lambda_all_decline_degenerate():
    trials = [
        ("g1", "unhurried", "decline", 1500),
        ("g2", "unhurried", "decline", 1400),
        ("g3", "unhurried", "decline", 1300),
        ("g4", "unhurried", "decline", 1200),
        ("g1", "hurried", "decline", 900),
        ("g2", "hurried", "decline", 800),
        ("g3", "hurried", "decline", 700),
        ("g4", "hurried", "decline", 600),
    ]
    infs = _by_construct(score_round("choice", _events(trials)))
    la = infs["loss_aversion"]
    assert la.confidence < 0.2
    assert la.evidence.get("unidentified") is True


def test_lambda_all_take_degenerate():
    trials = [
        ("g1", "unhurried", "take", 1500),
        ("g2", "unhurried", "take", 1400),
        ("g3", "unhurried", "take", 1300),
        ("g4", "unhurried", "take", 1200),
        ("g1", "hurried", "take", 900),
        ("g2", "hurried", "take", 800),
        ("g3", "hurried", "take", 700),
        ("g4", "hurried", "take", 600),
    ]
    infs = _by_construct(score_round("choice", _events(trials)))
    la = infs["loss_aversion"]
    assert la.confidence < 0.2
    assert la.evidence.get("unidentified") is True


def test_lambda_underpowered():
    trials = [
        ("g1", "unhurried", "decline", 1500),
        ("g2", "unhurried", "take", 1400),
        ("g3", "unhurried", "take", 1300),
        ("g4", "unhurried", "take", 1200),
        ("g1", "hurried", "abandon", 4000),
        ("g2", "hurried", "abandon", 4000),
        ("g3", "hurried", "abandon", 4000),
        ("g4", "hurried", "abandon", 4000),
    ]
    infs = _by_construct(score_round("choice", _events(trials)))
    la = infs["loss_aversion"]
    assert la.confidence <= 0.1
    assert la.evidence.get("underpowered") is True


# --- risk tolerance --------------------------------------------------------


def test_risk_tolerance_per_condition():
    trials = [
        ("g1", "unhurried", "decline", 1500),
        ("g2", "unhurried", "take", 1400),
        ("g3", "unhurried", "take", 1300),
        ("g4", "unhurried", "take", 1200),
        ("g1", "hurried", "decline", 900),
        ("g2", "hurried", "decline", 800),
        ("g3", "hurried", "decline", 700),
        ("g4", "hurried", "take", 600),
    ]
    infs = _by_construct(score_round("choice", _events(trials)))
    rt = infs["risk_tolerance"]
    assert rt.value["overall_take_rate"] == pytest.approx(0.5)
    assert rt.value["unhurried"] == pytest.approx(0.75)
    assert rt.value["hurried"] == pytest.approx(0.25)
    assert rt.confidence == pytest.approx(1.0)


# --- stress response delta -------------------------------------------------


def test_stress_response_delta_consistent():
    trials = [
        ("g1", "unhurried", "take", 1500),
        ("g2", "unhurried", "take", 1400),
        ("g3", "unhurried", "take", 1300),
        ("g4", "unhurried", "take", 1200),
        ("g1", "hurried", "decline", 900),
        ("g2", "hurried", "decline", 800),
        ("g3", "hurried", "decline", 700),
        ("g4", "hurried", "decline", 600),
    ]
    infs = _by_construct(score_round("choice", _events(trials)))
    sr = infs["stress_response"]
    assert sr.value["take_rate_delta"] == pytest.approx(-1.0)
    assert sr.confidence >= 0.7


def test_stress_response_delta_noisy():
    trials = [
        ("g1", "unhurried", "take", 1500),
        ("g2", "unhurried", "decline", 1400),
        ("g3", "unhurried", "take", 1300),
        ("g4", "unhurried", "decline", 1200),
        ("g1", "hurried", "decline", 900),
        ("g2", "hurried", "take", 800),
        ("g3", "hurried", "take", 700),
        ("g4", "hurried", "decline", 600),
    ]
    infs = _by_construct(score_round("choice", _events(trials)))
    sr = infs["stress_response"]
    assert sr.confidence < 0.4
