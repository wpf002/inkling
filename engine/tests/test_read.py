"""Engine tests for Round 5 (Read) scoring."""
from __future__ import annotations

import json
from pathlib import Path

from inkling_engine import score_round

SCENARIOS_PATH = (
    Path(__file__).resolve().parents[2]
    / "content"
    / "rounds"
    / "read"
    / "scenarios.json"
)
SCENARIOS = json.loads(SCENARIOS_PATH.read_text())["scenarios"]


def _events(picks: list[tuple[str, int]]) -> list[dict]:
    """picks[i] = (option_id, rt_ms) aligned to SCENARIOS[i]."""
    events: list[dict] = []
    t = 0
    for i, scenario in enumerate(SCENARIOS[: len(picks)]):
        opt_id, rt = picks[i]
        events.append(
            {
                "event_type": "scenario_shown",
                "payload": {"scenario_id": scenario["id"], "index": i},
                "t_ms": t,
            }
        )
        t += rt
        opt = next(o for o in scenario["options"] if o["id"] == opt_id)
        events.append(
            {
                "event_type": "option_selected",
                "payload": {
                    "scenario_id": scenario["id"],
                    "index": i,
                    "option_id": opt_id,
                    "tags": opt["tags"],
                    "rt_ms": rt,
                },
                "t_ms": t,
            }
        )
        t += 200
    return events


def _by_construct(infs):
    return {i.construct: i for i in infs}


def test_typical_mixed_attribution():
    # Mix of hostile/benign and internal/external.
    picks = [
        ("a", 4000), ("b", 4500), ("c", 5000), ("b", 4700),
        ("d", 4200), ("b", 5100), ("a", 4800), ("b", 4900),
    ]
    infs = _by_construct(score_round("read", _events(picks)))
    a = infs["attribution_style"]
    assert 0.0 <= a.value["hostile_score"] <= 1.0
    assert 0.0 <= a.value["internal_score"] <= 1.0
    assert a.confidence == 1.0
    d = infs["deliberation"]
    assert d.confidence == 0.7


def test_extreme_hostile_internal_player():
    # Pick the maximally hostile-internal option where one exists; fall
    # back to first hostile option otherwise.
    picks: list[tuple[str, int]] = []
    for s in SCENARIOS:
        hostile_internal = next(
            (o for o in s["options"] if "hostile" in o["tags"] and "internal" in o["tags"]),
            None,
        )
        if hostile_internal is None:
            hostile_internal = next(o for o in s["options"] if "hostile" in o["tags"])
        picks.append((hostile_internal["id"], 5000))
    infs = _by_construct(score_round("read", _events(picks)))
    a = infs["attribution_style"]
    assert a.value["hostile_score"] == 1.0
    assert a.value["internal_score"] >= 0.5
    assert a.confidence == 1.0


def test_underpowered_three_scenarios():
    picks = [("b", 4000), ("b", 4500), ("c", 5000)]
    infs = _by_construct(score_round("read", _events(picks)))
    a = infs["attribution_style"]
    assert a.confidence < 0.5
    assert a.evidence.get("underpowered") is True
    d = infs["deliberation"]
    assert d.confidence == 0.7  # floor still applies
