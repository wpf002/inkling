import json
import uuid
from pathlib import Path

import pytest
from sqlalchemy import select

from app.models.inference import Inference

GAMBLES = {
    g["id"]: g
    for g in json.loads(
        (
            Path(__file__).resolve().parents[2]
            / "content"
            / "rounds"
            / "choice"
            / "gambles.json"
        ).read_text()
    )["gambles"]
}


def _new_token() -> str:
    return str(uuid.uuid4())


def _trial_events(trials: list[tuple[str, str, str, int]]) -> list[dict]:
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
        t += 50 + i
    return out


async def _seeded_session(client, consent_payload) -> str:
    token = _new_token()
    await client.post(
        "/sessions",
        json={
            "consent": consent_payload,
            "age_attested": True,
            "anonymous_token": token,
        },
    )
    trials = [
        ("g1", "unhurried", "decline", 1500),
        ("g2", "unhurried", "take", 1400),
        ("g3", "unhurried", "take", 1300),
        ("g4", "unhurried", "take", 1200),
        ("g1", "hurried", "decline", 900),
        ("g2", "hurried", "decline", 800),
        ("g3", "hurried", "take", 700),
        ("g4", "hurried", "take", 700),
    ]
    resp = await client.post(
        f"/sessions/{token}/round-events",
        json={"round": "choice", "events": _trial_events(trials)},
        headers={"X-Inkling-Session": token},
    )
    assert resp.status_code == 201, resp.text
    return token


@pytest.mark.asyncio
async def test_round_complete_writes_three_inferences(client, session, consent_payload):
    token = await _seeded_session(client, consent_payload)
    resp = await client.post(
        f"/sessions/{token}/round-complete",
        json={"round": "choice"},
        headers={"X-Inkling-Session": token},
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    by_construct = {i["construct"]: i for i in body["inferences"]}
    assert set(by_construct) == {"loss_aversion", "risk_tolerance", "stress_response"}
    assert by_construct["loss_aversion"]["tier"] == "high"
    assert by_construct["risk_tolerance"]["tier"] == "high"
    assert by_construct["stress_response"]["tier"] == "medium"

    rows = (await session.execute(select(Inference))).scalars().all()
    assert len(rows) == 3
    assert {r.construct for r in rows} == {"loss_aversion", "risk_tolerance", "stress_response"}


@pytest.mark.asyncio
async def test_round_complete_is_idempotent(client, session, consent_payload):
    token = await _seeded_session(client, consent_payload)
    first = await client.post(
        f"/sessions/{token}/round-complete",
        json={"round": "choice"},
        headers={"X-Inkling-Session": token},
    )
    assert first.status_code == 200
    first_body = first.json()

    second = await client.post(
        f"/sessions/{token}/round-complete",
        json={"round": "choice"},
        headers={"X-Inkling-Session": token},
    )
    assert second.status_code == 200
    assert second.json() == first_body

    rows = (await session.execute(select(Inference))).scalars().all()
    assert len(rows) == 3


@pytest.mark.asyncio
async def test_round_complete_unknown_round_400(client, consent_payload):
    token = _new_token()
    await client.post(
        "/sessions",
        json={
            "consent": consent_payload,
            "age_attested": True,
            "anonymous_token": token,
        },
    )
    resp = await client.post(
        f"/sessions/{token}/round-complete",
        json={"round": "nope"},
        headers={"X-Inkling-Session": token},
    )
    assert resp.status_code == 400


@pytest.mark.asyncio
async def test_get_inferences_returns_persisted(client, consent_payload):
    token = await _seeded_session(client, consent_payload)
    await client.post(
        f"/sessions/{token}/round-complete",
        json={"round": "choice"},
        headers={"X-Inkling-Session": token},
    )

    resp = await client.get(
        f"/sessions/{token}/inferences",
        params={"round": "choice"},
        headers={"X-Inkling-Session": token},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert {i["construct"] for i in body["inferences"]} == {
        "loss_aversion",
        "risk_tolerance",
        "stress_response",
    }


@pytest.mark.asyncio
async def test_resume_discards_prior_attempt_events(client, session, consent_payload):
    """Resume rule: events before the last round_start are ignored.

    A player who closes the tab mid-round and replays should have
    their final attempt scored, not the abandoned one.
    """
    token = _new_token()
    await client.post(
        "/sessions",
        json={
            "consent": consent_payload,
            "age_attested": True,
            "anonymous_token": token,
        },
    )

    # Attempt 1: all takes — scorer would emit unidentified (one-choice).
    attempt_1_round_start = {
        "event_type": "round_start",
        "payload": {"gambles_count": 8, "attempt": 1},
        "t_ms": 0,
    }
    attempt_1_trials = [
        ("g1", "unhurried", "take", 1000),
        ("g2", "unhurried", "take", 1000),
        ("g3", "unhurried", "take", 1000),
        ("g4", "unhurried", "take", 1000),
        ("g1", "hurried", "take", 800),
        ("g2", "hurried", "take", 800),
        ("g3", "hurried", "take", 800),
        ("g4", "hurried", "take", 800),
    ]
    # Attempt 2: mixed — population-mean-ish player.
    attempt_2_round_start = {
        "event_type": "round_start",
        "payload": {"gambles_count": 8, "attempt": 2},
        "t_ms": 50000,
    }
    attempt_2_trials = [
        ("g1", "unhurried", "decline", 1500),
        ("g2", "unhurried", "decline", 1400),
        ("g3", "unhurried", "take", 1100),
        ("g4", "unhurried", "take", 1000),
        ("g1", "hurried", "decline", 900),
        ("g2", "hurried", "decline", 800),
        ("g3", "hurried", "take", 700),
        ("g4", "hurried", "take", 700),
    ]

    events = (
        [attempt_1_round_start]
        + _trial_events(attempt_1_trials)
        + [attempt_2_round_start]
        + _trial_events(attempt_2_trials)
    )

    # Re-stamp t_ms so attempt-2 events sit after attempt 1.
    for i, ev in enumerate(events):
        ev["t_ms"] = i * 100

    # Post in two batches under the 200-event cap.
    half = len(events) // 2
    for batch in (events[:half], events[half:]):
        resp = await client.post(
            f"/sessions/{token}/round-events",
            json={"round": "choice", "events": batch},
            headers={"X-Inkling-Session": token},
        )
        assert resp.status_code == 201, resp.text

    resp = await client.post(
        f"/sessions/{token}/round-complete",
        json={"round": "choice"},
        headers={"X-Inkling-Session": token},
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    by_construct = {i["construct"]: i for i in body["inferences"]}

    # Attempt 1's all-takes would yield unidentified=True. Attempt 2
    # has a mix and should yield an identifiable fit (no unidentified
    # flag). If the trim didn't work we'd see attempt 1's signature.
    la = by_construct["loss_aversion"]
    assert la["evidence"].get("unidentified") is not True
    assert la["evidence"]["trials_used"] == 8  # only attempt 2's 8 trials

    rt = by_construct["risk_tolerance"]
    # Attempt 1: take rate 1.0. Attempt 2: 4/8 = 0.5. Trim → 0.5.
    assert rt["value"]["overall_take_rate"] == pytest.approx(0.5)


@pytest.mark.asyncio
async def test_get_inferences_empty_before_scoring(client, consent_payload):
    token = await _seeded_session(client, consent_payload)
    resp = await client.get(
        f"/sessions/{token}/inferences",
        params={"round": "choice"},
        headers={"X-Inkling-Session": token},
    )
    assert resp.status_code == 200
    assert resp.json() == {"inferences": []}
