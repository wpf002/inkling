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
async def test_get_inferences_empty_before_scoring(client, consent_payload):
    token = await _seeded_session(client, consent_payload)
    resp = await client.get(
        f"/sessions/{token}/inferences",
        params={"round": "choice"},
        headers={"X-Inkling-Session": token},
    )
    assert resp.status_code == 200
    assert resp.json() == {"inferences": []}
