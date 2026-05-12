"""Engine tests for Round 2 (Pursuit) scoring."""
from __future__ import annotations

import json
from pathlib import Path

from inkling_engine import score_round

TRIALS_PATH = (
    Path(__file__).resolve().parents[2]
    / "content"
    / "rounds"
    / "pursuit"
    / "trials.json"
)
CONTENT = json.loads(TRIALS_PATH.read_text())
TRIALS = CONTENT["trials"]
SPIKE_INDICES = CONTENT["spike_indices"]


def _events(outcomes: list[tuple[str, int | None]]) -> list[dict]:
    """outcomes[i] = (outcome, rt_ms_or_None) aligned to TRIALS[i].

    outcome ∈ {"click", "miss"}.
    """
    events: list[dict] = [
        {
            "event_type": "round_start",
            "payload": {"spike_indices": SPIKE_INDICES, "trials_count": len(TRIALS)},
            "t_ms": 0,
        }
    ]
    t = 0
    for i, (outcome, rt) in enumerate(outcomes):
        trial = TRIALS[i]
        events.append(
            {
                "event_type": "trial_shown",
                "payload": {
                    "trial": trial["id"],
                    "index": i,
                    "target_type": trial["target_type"],
                    "window_ms": trial["window_ms"],
                },
                "t_ms": t,
            }
        )
        t += rt if rt is not None else trial["window_ms"]
        events.append(
            {
                "event_type": outcome,
                "payload": {
                    "trial": trial["id"],
                    "index": i,
                    "target_type": trial["target_type"],
                    "rt_ms": rt,
                },
                "t_ms": t,
            }
        )
        t += 350
    return events


def _by_construct(infs):
    return {i.construct: i for i in infs}


def test_typical_player_lands_in_bands():
    # Typical: hits all valids around ~520ms, ignores distractors, one
    # post-spike slowdown bump.
    outcomes: list[tuple[str, int | None]] = []
    for i, t in enumerate(TRIALS):
        if t["target_type"] == "distractor":
            outcomes.append(("miss", None))
            continue
        rt = 540
        if i - 1 in SPIKE_INDICES or i in SPIKE_INDICES:
            rt = 720
        outcomes.append(("click", rt))
    infs = _by_construct(score_round("pursuit", _events(outcomes)))
    rtp = infs["reaction_time_profile"]
    assert 400 <= rtp.value["median_rt_ms"] <= 800
    assert rtp.value["coefficient_of_variation"] >= 0.0
    assert rtp.confidence >= 0.9
    sa = infs["sustained_attention"]
    assert isinstance(sa.value["rt_slope_ms_per_trial"], float)
    ri = infs["response_inhibition"]
    assert ri.value["false_alarm_rate"] == 0.0
    assert ri.value["hit_rate"] >= 0.9
    ft = infs["frustration_tolerance"]
    # Post-spike bump should be positive on average.
    assert ft.value["post_spike_rt_delta_ms"] > 0


def test_extreme_player_fast_rt_profile():
    outcomes = [
        ("click", 320) if t["target_type"] == "valid" else ("miss", None)
        for t in TRIALS
    ]
    infs = _by_construct(score_round("pursuit", _events(outcomes)))
    rtp = infs["reaction_time_profile"]
    assert rtp.value["median_rt_ms"] == 320
    assert rtp.confidence == 1.0
    assert rtp.value["coefficient_of_variation"] == 0.0


def test_underpowered_player_short_session():
    # Player only completes the first 6 trials, then drops off.
    outcomes: list[tuple[str, int | None]] = []
    for t in TRIALS[:6]:
        outcomes.append(("click", 500) if t["target_type"] == "valid" else ("miss", None))
    infs = _by_construct(score_round("pursuit", _events(outcomes)))
    rtp = infs["reaction_time_profile"]
    assert rtp.confidence < 0.5
    assert rtp.evidence.get("underpowered") is True
    ft = infs["frustration_tolerance"]
    assert ft.evidence.get("underpowered") is True


def test_false_alarms_on_distractors():
    outcomes = [
        ("click", 500) for _ in TRIALS  # clicks on everything including distractors
    ]
    infs = _by_construct(score_round("pursuit", _events(outcomes)))
    ri = infs["response_inhibition"]
    assert ri.value["false_alarm_rate"] == 1.0
    assert ri.value["hit_rate"] == 1.0
