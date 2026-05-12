"""Engine tests for Round 3 (Trust) scoring."""
from __future__ import annotations

import json
from pathlib import Path

from inkling_engine import score_round

NPCS_PATH = (
    Path(__file__).resolve().parents[2]
    / "content"
    / "rounds"
    / "trust"
    / "npcs.json"
)
CONTENT = json.loads(NPCS_PATH.read_text())
TRIALS = CONTENT["trials"]


def _events(plays: list[tuple[str, int, int]]) -> list[dict]:
    """plays[i] = (npc_id, send_amount, received_amount) aligned to TRIALS[i]."""
    events: list[dict] = []
    t = 0
    for i, trial in enumerate(TRIALS):
        npc_id, send, recv = plays[i]
        events.append(
            {
                "event_type": "trial_shown",
                "payload": {
                    "trial_id": trial["trial_id"],
                    "npc_id": trial["npc_id"],
                    "first": trial["first"],
                },
                "t_ms": t,
            }
        )
        t += 100
        events.append(
            {
                "event_type": "send_amount",
                "payload": {
                    "trial_id": trial["trial_id"],
                    "npc_id": trial["npc_id"],
                    "amount": send,
                },
                "t_ms": t,
            }
        )
        t += 50
        events.append(
            {
                "event_type": "outcome_revealed",
                "payload": {
                    "trial_id": trial["trial_id"],
                    "npc_id": trial["npc_id"],
                    "received": recv,
                },
                "t_ms": t,
            }
        )
        t += 50
    return events


def _by_construct(infs):
    return {i.construct: i for i in infs}


def test_typical_player_bands():
    # Player sends 5 first across all NPCs; reacts to history thereafter.
    plays = [
        ("npc_a", 5, 8),
        ("npc_b", 5, 1),
        ("npc_c", 5, 11),
        ("npc_d", 5, 6),
        ("npc_a", 6, 9),   # rewarded fair-share → up
        ("npc_b", 2, 0),   # punished selfish → way down
        ("npc_c", 7, 15),  # rewarded generous → up
        ("npc_d", 5, 4),
    ]
    infs = _by_construct(score_round("trust", _events(plays)))
    it = infs["initial_trust_propensity"]
    assert it.value["initial_trust_amount"] == 5.0
    assert it.confidence == 1.0
    ar = infs["adaptation_rate"]
    assert ar.value["n_pairs"] == 4
    # Players who scale by received → positive correlation.
    assert ar.value["adaptation_correlation"] > 0.4
    rt = infs["retaliation_tendency"]
    assert rt.value["retaliation_delta"] < 0  # send below baseline after selfish


def test_extreme_first_trust_maximally_high():
    plays = [
        ("npc_a", 10, 15),
        ("npc_b", 10, 1),
        ("npc_c", 10, 21),
        ("npc_d", 10, 14),
        ("npc_a", 10, 15),
        ("npc_b", 10, 1),
        ("npc_c", 10, 21),
        ("npc_d", 10, 14),
    ]
    infs = _by_construct(score_round("trust", _events(plays)))
    it = infs["initial_trust_propensity"]
    assert it.value["initial_trust_amount"] == 10.0
    assert it.value["sd"] == 0.0
    assert it.confidence == 1.0


def test_underpowered_player_missing_first_trial():
    # Player skipped the first round of npcs entirely (event stream
    # starts mid-flow). All first-trial flags are False to simulate.
    plays = [
        ("npc_a", 5, 8),
        ("npc_b", 5, 1),
        ("npc_c", 5, 11),
        ("npc_d", 5, 6),
    ]
    # Build truncated events
    events: list[dict] = []
    t = 0
    for i, trial in enumerate(TRIALS[4:]):
        npc_id, send, recv = plays[i]
        events.append(
            {
                "event_type": "send_amount",
                "payload": {
                    "trial_id": trial["trial_id"],
                    "npc_id": trial["npc_id"],
                    "amount": send,
                    "first": False,
                },
                "t_ms": t,
            }
        )
        t += 50
        events.append(
            {
                "event_type": "outcome_revealed",
                "payload": {
                    "trial_id": trial["trial_id"],
                    "npc_id": trial["npc_id"],
                    "received": recv,
                },
                "t_ms": t,
            }
        )
        t += 50
    infs = _by_construct(score_round("trust", events))
    it = infs["initial_trust_propensity"]
    assert it.evidence.get("underpowered") is True
    assert it.confidence < 0.5
