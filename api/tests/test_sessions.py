import uuid

import pytest
from sqlalchemy import select

from app.models.self_report import SelfReport
from app.models.session import Session


def _new_token() -> str:
    return str(uuid.uuid4())


@pytest.mark.asyncio
async def test_create_session_persists_consent(client, session, consent_payload):
    token = _new_token()
    resp = await client.post(
        "/sessions",
        json={
            "consent": consent_payload,
            "age_attested": True,
            "anonymous_token": token,
        },
    )
    assert resp.status_code == 201, resp.text
    body = resp.json()
    assert body["anonymous_token"] == token
    assert "session_id" in body

    row = (
        await session.execute(select(Session).where(Session.anonymous_token == token))
    ).scalar_one()
    assert row.age_attested is True
    assert row.consent["gameplay"] is True
    assert row.consent["research_aggregate"] is False


@pytest.mark.asyncio
async def test_get_session_requires_header(client, consent_payload):
    token = _new_token()
    await client.post(
        "/sessions",
        json={
            "consent": consent_payload,
            "age_attested": True,
            "anonymous_token": token,
        },
    )

    resp = await client.get(f"/sessions/{token}")
    assert resp.status_code == 401

    resp = await client.get(f"/sessions/{token}", headers={"X-Inkling-Session": token})
    assert resp.status_code == 200
    body = resp.json()
    assert body["anonymous_token"] == token
    assert body["has_self_report"] is False


@pytest.mark.asyncio
async def test_get_session_rejects_mismatched_header(client, consent_payload):
    token = _new_token()
    await client.post(
        "/sessions",
        json={
            "consent": consent_payload,
            "age_attested": True,
            "anonymous_token": token,
        },
    )
    other = _new_token()
    resp = await client.get(f"/sessions/{token}", headers={"X-Inkling-Session": other})
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_self_report_submission(client, session, consent_payload):
    token = _new_token()
    await client.post(
        "/sessions",
        json={
            "consent": consent_payload,
            "age_attested": True,
            "anonymous_token": token,
        },
    )

    payload = {
        "responses": [
            {"item_id": "sr01", "response": 3},
            {"item_id": "sr02", "response": 5},
            {"item_id": "sr03", "response": 1},
            {"item_id": "sr04", "response": 4},
            {"item_id": "sr05", "response": 2},
            {"item_id": "sr06", "response": 4},
            {"item_id": "sr07", "response": 3},
            {"item_id": "sr08", "response": 2},
            {"item_id": "sr09", "response": 5},
            {"item_id": "sr10", "response": 3},
        ]
    }
    resp = await client.post(
        f"/sessions/{token}/self-report",
        json=payload,
        headers={"X-Inkling-Session": token},
    )
    assert resp.status_code == 201, resp.text
    assert resp.json() == {"saved": 10}

    rows = (await session.execute(select(SelfReport))).scalars().all()
    assert len(rows) == 10
    assert {r.item_id for r in rows} == {f"sr{i:02d}" for i in range(1, 11)}


@pytest.mark.asyncio
async def test_self_report_rejected_without_age_attestation(client, consent_payload):
    token = _new_token()
    await client.post(
        "/sessions",
        json={
            "consent": consent_payload,
            "age_attested": False,
            "anonymous_token": token,
        },
    )

    resp = await client.post(
        f"/sessions/{token}/self-report",
        json={"responses": [{"item_id": "sr01", "response": 3}]},
        headers={"X-Inkling-Session": token},
    )
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_self_report_rejects_unknown_item(client, consent_payload):
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
        f"/sessions/{token}/self-report",
        json={"responses": [{"item_id": "sr99", "response": 3}]},
        headers={"X-Inkling-Session": token},
    )
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_soft_and_hard_delete_session_cascades(client, session, consent_payload):
    token = _new_token()
    create = await client.post(
        "/sessions",
        json={
            "consent": consent_payload,
            "age_attested": True,
            "anonymous_token": token,
        },
    )
    session_id = create.json()["session_id"]
    await client.post(
        f"/sessions/{token}/self-report",
        json={"responses": [{"item_id": "sr01", "response": 3}]},
        headers={"X-Inkling-Session": token},
    )

    # Sanity: a self_report row exists.
    rows = (await session.execute(select(SelfReport))).scalars().all()
    assert len(rows) == 1

    resp = await client.delete(f"/sessions/{token}", headers={"X-Inkling-Session": token})
    assert resp.status_code == 202

    # After background hard-delete runs, the session row is gone and so are its children.
    remaining_session = (
        await session.execute(select(Session).where(Session.id == uuid.UUID(session_id)))
    ).scalar_one_or_none()
    assert remaining_session is None
    remaining_reports = (await session.execute(select(SelfReport))).scalars().all()
    assert remaining_reports == []

    # Subsequent fetch returns 404.
    resp = await client.get(f"/sessions/{token}", headers={"X-Inkling-Session": token})
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_content_self_report_items(client):
    resp = await client.get("/content/self-report-items")
    assert resp.status_code == 200
    items = resp.json()["items"]
    assert len(items) == 10
    assert {i["id"] for i in items} == {f"sr{i:02d}" for i in range(1, 11)}
    assert items[0]["construct"]
    assert items[0]["scale"] == "likert_5"
