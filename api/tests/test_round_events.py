import json
import uuid
from pathlib import Path

import pytest
from sqlalchemy import select

from app.models.round_event import RoundEvent

GAMBLES = json.loads(
    (
        Path(__file__).resolve().parents[2]
        / "content"
        / "rounds"
        / "choice"
        / "gambles.json"
    ).read_text()
)["gambles"]


def _new_token() -> str:
    return str(uuid.uuid4())


async def _create_session(client, consent_payload, *, age_attested: bool = True) -> str:
    token = _new_token()
    resp = await client.post(
        "/sessions",
        json={
            "consent": consent_payload,
            "age_attested": age_attested,
            "anonymous_token": token,
        },
    )
    assert resp.status_code == 201, resp.text
    return token


@pytest.mark.asyncio
async def test_round_events_batch_persists(client, session, consent_payload):
    token = await _create_session(client, consent_payload)
    g = GAMBLES[0]
    payload = {
        "round": "choice",
        "events": [
            {"event_type": "round_start", "payload": {"order": ["unhurried", "hurried"]}, "t_ms": 0},
            {
                "event_type": "gamble_shown",
                "payload": {"trial": "t1", "gamble_id": g["id"], "win": g["win"], "lose": g["lose"]},
                "t_ms": 100,
            },
            {
                "event_type": "choice",
                "payload": {"trial": "t1", "gamble_id": g["id"], "value": "take", "rt_ms": 1200},
                "t_ms": 1300,
            },
        ],
    }
    resp = await client.post(
        f"/sessions/{token}/round-events",
        json=payload,
        headers={"X-Inkling-Session": token},
    )
    assert resp.status_code == 201, resp.text
    assert resp.json() == {"accepted": 3}

    rows = (await session.execute(select(RoundEvent))).scalars().all()
    assert len(rows) == 3
    assert {r.event_type for r in rows} == {"round_start", "gamble_shown", "choice"}
    assert all(r.round == "choice" for r in rows)


@pytest.mark.asyncio
async def test_round_events_requires_header(client, consent_payload):
    token = await _create_session(client, consent_payload)
    payload = {"round": "choice", "events": [{"event_type": "x", "payload": {}, "t_ms": 0}]}
    resp = await client.post(f"/sessions/{token}/round-events", json=payload)
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_round_events_rejects_mismatched_header(client, consent_payload):
    token = await _create_session(client, consent_payload)
    payload = {"round": "choice", "events": [{"event_type": "x", "payload": {}, "t_ms": 0}]}
    resp = await client.post(
        f"/sessions/{token}/round-events",
        json=payload,
        headers={"X-Inkling-Session": _new_token()},
    )
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_round_events_unknown_round_400(client, consent_payload):
    token = await _create_session(client, consent_payload)
    payload = {"round": "not-a-round", "events": [{"event_type": "x", "payload": {}, "t_ms": 0}]}
    resp = await client.post(
        f"/sessions/{token}/round-events",
        json=payload,
        headers={"X-Inkling-Session": token},
    )
    assert resp.status_code == 400


@pytest.mark.asyncio
async def test_round_events_validation_rejects_bad_shape(client, consent_payload):
    token = await _create_session(client, consent_payload)
    bad = {
        "round": "choice",
        "events": [
            {"event_type": "", "payload": {}, "t_ms": 0},  # empty type
        ],
    }
    resp = await client.post(
        f"/sessions/{token}/round-events",
        json=bad,
        headers={"X-Inkling-Session": token},
    )
    assert resp.status_code == 422

    negative_t = {
        "round": "choice",
        "events": [{"event_type": "x", "payload": {}, "t_ms": -1}],
    }
    resp = await client.post(
        f"/sessions/{token}/round-events",
        json=negative_t,
        headers={"X-Inkling-Session": token},
    )
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_round_events_age_attestation_required(client, consent_payload):
    token = await _create_session(client, consent_payload, age_attested=False)
    payload = {"round": "choice", "events": [{"event_type": "x", "payload": {}, "t_ms": 0}]}
    resp = await client.post(
        f"/sessions/{token}/round-events",
        json=payload,
        headers={"X-Inkling-Session": token},
    )
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_content_round_gambles(client):
    resp = await client.get("/content/round-gambles", params={"round": "choice"})
    assert resp.status_code == 200
    body = resp.json()
    assert body["round_id"] == "choice"
    assert len(body["gambles"]) == 4
    assert body["conditions"] == ["unhurried", "hurried"]
    assert body["hurry_ms"] == 4000
    assert body["alpha"] == 0.88


@pytest.mark.asyncio
async def test_content_round_gambles_unknown_round_400(client):
    resp = await client.get("/content/round-gambles", params={"round": "nope"})
    assert resp.status_code == 400
