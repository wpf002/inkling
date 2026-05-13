"""API-level tests for POST /sessions/{token}/overreach.

Covers:
  - Idempotency: a second call within the rate limit returns the same row.
  - 429 once the per-IP rate limit is exceeded.
  - 503 when the daily cost cap is exceeded.
  - 503 when OVERREACH_ENABLED is false.

The Anthropic SDK is mocked at the engine layer via
`overreach_module.score_overreach` so the API never reaches the real
network. We monkeypatch the module-level function for the duration of
each test.
"""
from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any

import pytest
from sqlalchemy import select

from app.core.config import get_settings
from app.models.daily_spend import DailySpend
from app.services.rate_limit import overreach_limiter

# A canned, lexicon-clean overreach payload the mocked engine returns.
CLEAN_PAYLOAD: dict[str, Any] = {
    "big_five": {
        "O": {"score": 60, "blurb": "Curious about new tools and frames."},
        "C": {"score": 70, "blurb": "Methodical when stakes rise."},
        "E": {"score": 45, "blurb": "Selective about social investment."},
        "A": {"score": 55, "blurb": "Even-keeled in cooperative play."},
        "N": {"score": 40, "blurb": "Steady under timed pressure."},
    },
    "political_values": "Center-pragmatic with a preference for outcome-led frames.",
    "life_history": "Late-stage career, partnered, college-educated.",
    "consumer_profile": "Premium subscription tolerant, late-cycle adopter.",
}


def _make_inference_row(_summary: dict[str, Any], **_: Any):
    """Stand-in for `score_overreach` that bypasses the LLM."""
    from inkling_engine.llm.overreach import OverreachResult
    from inkling_engine.models import Inference

    return OverreachResult(
        inference=Inference(
            construct="overreach",
            tier="overreach",
            value=CLEAN_PAYLOAD,
            confidence=0.5,
            evidence={
                "model": "test-model",
                "input_token_count": 1200,
                "output_token_count": 400,
                "prompt_version": "test-vN",
                "retried_on_lexicon": False,
                "estimated_cost_usd": 0.0096,
            },
        ),
        cost_usd=0.0096,
        input_tokens=1200,
        output_tokens=400,
    )


@pytest.fixture(autouse=True)
def reset_state(monkeypatch: pytest.MonkeyPatch):
    """Reset the in-memory rate limiter and the cached settings for every test."""
    overreach_limiter.reset()
    get_settings.cache_clear()
    yield
    overreach_limiter.reset()
    get_settings.cache_clear()


@pytest.fixture
def patch_engine_call(monkeypatch: pytest.MonkeyPatch):
    """Replace the engine call inside overreach_service with a mock."""
    from inkling_engine.llm import overreach as engine_overreach

    monkeypatch.setattr(
        engine_overreach, "score_overreach", _make_inference_row
    )


async def _create_session(client, consent_payload, age_attested=True) -> str:
    token = str(uuid.uuid4())
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


async def test_overreach_creates_then_returns_cached_row(client, consent_payload, patch_engine_call, session):
    token = await _create_session(client, consent_payload)
    resp = await client.post(
        f"/sessions/{token}/overreach",
        json={},
        headers={"X-Inkling-Session": token},
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["cached"] is False
    assert body["inference"]["construct"] == "overreach"

    # Second call within rate limit returns cached.
    resp2 = await client.post(
        f"/sessions/{token}/overreach",
        json={},
        headers={"X-Inkling-Session": token},
    )
    assert resp2.status_code == 200
    assert resp2.json()["cached"] is True
    # The persisted value should match the mocked payload.
    assert resp2.json()["inference"]["value"] == CLEAN_PAYLOAD


async def test_rate_limit_after_three_calls(client, consent_payload, patch_engine_call, monkeypatch):
    monkeypatch.setenv("OVERREACH_RATE_LIMIT_PER_HOUR", "3")
    get_settings.cache_clear()

    # Three different sessions so we don't short-circuit on idempotency.
    tokens = []
    for _ in range(3):
        tokens.append(await _create_session(client, consent_payload))
    for tk in tokens:
        resp = await client.post(
            f"/sessions/{tk}/overreach", json={}, headers={"X-Inkling-Session": tk}
        )
        assert resp.status_code == 200, resp.text

    # Fourth session, same client IP — should 429 because no cached row exists.
    fourth = await _create_session(client, consent_payload)
    resp = await client.post(
        f"/sessions/{fourth}/overreach",
        json={},
        headers={"X-Inkling-Session": fourth},
    )
    assert resp.status_code == 429, resp.text
    assert "Retry-After" in resp.headers


async def test_cost_cap_returns_503(client, consent_payload, patch_engine_call, monkeypatch, session):
    monkeypatch.setenv("OVERREACH_DAILY_USD_CAP", "0.01")
    get_settings.cache_clear()

    # Pre-seed today's spend so the cap is already hit.
    today = datetime.now(UTC).date()
    session.add(DailySpend(date=today, total_usd=0.99, call_count=1))
    await session.commit()

    token = await _create_session(client, consent_payload)
    resp = await client.post(
        f"/sessions/{token}/overreach",
        json={},
        headers={"X-Inkling-Session": token},
    )
    assert resp.status_code == 503
    body = resp.json()
    detail = body["detail"].lower()
    # Human-voice copy: should mention the daily limit being hit and that
    # the rest still works.
    assert "daily limit" in detail or "tomorrow" in detail


async def test_overreach_disabled_returns_503(client, consent_payload, patch_engine_call, monkeypatch):
    monkeypatch.setenv("OVERREACH_ENABLED", "false")
    get_settings.cache_clear()

    token = await _create_session(client, consent_payload)
    resp = await client.post(
        f"/sessions/{token}/overreach",
        json={},
        headers={"X-Inkling-Session": token},
    )
    assert resp.status_code == 503
    assert "paused" in resp.json()["detail"].lower()


async def test_persisted_inference_passes_lexicon_check(client, consent_payload, patch_engine_call, session):
    """End-to-end: create overreach, fetch persisted row, run lexicon
    filter against it. The mocked payload is clean so this should pass."""
    from inkling_engine.llm.lexicon_filter import find_violations

    from app.models.inference import Inference as InferenceRow

    token = await _create_session(client, consent_payload)
    resp = await client.post(
        f"/sessions/{token}/overreach",
        json={},
        headers={"X-Inkling-Session": token},
    )
    assert resp.status_code == 200

    rows = (
        await session.execute(
            select(InferenceRow).where(InferenceRow.construct == "overreach")
        )
    ).scalars().all()
    assert len(rows) == 1
    hits = find_violations(rows[0].value)
    assert hits == [], f"persisted overreach row contains forbidden vocab: {hits}"
