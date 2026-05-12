"""Engine tests for Round 4 (Memory) scoring."""
from __future__ import annotations

from inkling_engine import score_round


def _events(trials: list[tuple[int, bool, list[int]]]) -> list[dict]:
    """trials[i] = (span, correct, tap_rts_ms)."""
    events: list[dict] = [
        {
            "event_type": "round_start",
            "payload": {"start_span": 3},
            "t_ms": 0,
        }
    ]
    t = 100
    for i, (span, correct, rts) in enumerate(trials):
        tid = f"m{i + 1:02d}"
        events.append(
            {
                "event_type": "sequence_shown",
                "payload": {"trial_id": tid, "span": span},
                "t_ms": t,
            }
        )
        t += 1000
        events.append(
            {
                "event_type": "response",
                "payload": {
                    "trial_id": tid,
                    "span": span,
                    "correct": correct,
                    "tap_rts_ms": rts,
                },
                "t_ms": t,
            }
        )
        t += 300
    return events


def _by_construct(infs):
    return {i.construct: i for i in infs}


def test_typical_player_reaches_span_5():
    trials = [
        (3, True,  [600, 700, 650]),
        (3, True,  [620, 690, 660]),
        (4, True,  [700, 720, 700, 750]),
        (4, True,  [680, 710, 690, 720]),
        (5, True,  [800, 820, 800, 830, 810]),
        (5, False, [900, 910, 950, 980, 1000]),
        (6, False, [1100, 1200, 1100, 1300, 1200, 1400]),
        (6, False, [1150, 1180, 1200, 1250, 1300, 1350]),
    ]
    infs = _by_construct(score_round("memory", _events(trials)))
    span = infs["working_memory_span"]
    assert span.value["span"] == 5
    assert span.confidence == 1.0
    ps = infs["processing_speed"]
    assert ps.value["mean_tap_rt_ms"] > 600
    assert ps.confidence == 1.0
    pul = infs["performance_under_load"]
    assert pul.value["accuracy_at_low_span"] == 1.0
    assert pul.value["accuracy_at_high_span"] == 0.0
    assert pul.value["drop"] == 1.0


def test_extreme_high_span_player():
    trials = [
        (3, True, [400, 410, 420]),
        (4, True, [410, 420, 430, 440]),
        (5, True, [420, 430, 440, 450, 460]),
        (6, True, [430, 440, 450, 460, 470, 480]),
        (7, True, [440, 450, 460, 470, 480, 490, 500]),
        (8, True, [450, 460, 470, 480, 490, 500, 510, 520]),
    ]
    infs = _by_construct(score_round("memory", _events(trials)))
    span = infs["working_memory_span"]
    assert span.value["span"] == 8
    assert span.confidence == 1.0


def test_underpowered_player_three_trials():
    trials = [
        (3, True,  [600, 700, 650]),
        (3, False, [900, 910, 920]),
        (4, False, [1100, 1200, 1100, 1300]),
    ]
    infs = _by_construct(score_round("memory", _events(trials)))
    span = infs["working_memory_span"]
    assert span.confidence < 1.0
    pul = infs["performance_under_load"]
    assert pul.evidence.get("underpowered") is True
