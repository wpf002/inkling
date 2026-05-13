"""API-side wrapper around `inkling_engine.llm.overreach.score_overreach`.

Responsibilities:
  - Build the session_summary dict from the persisted state.
  - Idempotency: return the existing `construct="overreach"` Inference
    if one exists for the session.
  - Cost cap: refuse when today's spend would exceed the daily cap.
  - Cost tracking: increment `daily_spend.total_usd` after success.

Rate limiting is applied at the router level (per IP) — this service
does not know about HTTP.
"""
from __future__ import annotations

import uuid
from typing import Any

from inkling_engine.llm import overreach as overreach_engine
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.inference import Inference as InferenceRow
from app.models.round_event import RoundEvent
from app.models.self_report import SelfReport
from app.services import cost_cap


class OverreachDisabled(Exception):
    """The OVERREACH_ENABLED feature flag is false."""


class OverreachCostCapHit(Exception):
    """Today's total Anthropic spend would exceed the configured cap."""


class OverreachConfigMissing(Exception):
    """ANTHROPIC_API_KEY is not set or the SDK is unavailable."""


# Estimate used solely for the pre-call cap check. The real cost is
# computed after the call and recorded with `cost_cap.record_spend`.
EST_CALL_COST_USD = 0.05


async def existing_overreach_inference(
    db: AsyncSession, session_id: uuid.UUID
) -> InferenceRow | None:
    result = await db.execute(
        select(InferenceRow).where(
            InferenceRow.session_id == session_id,
            InferenceRow.construct == "overreach",
        )
    )
    return result.scalar_one_or_none()


async def _build_session_summary(
    db: AsyncSession, session_id: uuid.UUID
) -> dict[str, Any]:
    inf_result = await db.execute(
        select(InferenceRow)
        .where(InferenceRow.session_id == session_id)
        .order_by(InferenceRow.id)
    )
    inferences = inf_result.scalars().all()

    sr_result = await db.execute(
        select(SelfReport)
        .where(SelfReport.session_id == session_id)
        .order_by(SelfReport.id)
    )
    self_reports = sr_result.scalars().all()

    ev_result = await db.execute(
        select(RoundEvent.round).where(RoundEvent.session_id == session_id)
    )
    counts: dict[str, int] = {}
    for row in ev_result.all():
        counts[row[0]] = counts.get(row[0], 0) + 1

    return {
        "inferences": [
            {
                "construct": i.construct,
                "tier": i.tier,
                "value": i.value,
                "confidence": i.confidence,
            }
            for i in inferences
            if i.construct != "overreach"
        ],
        "self_report": [
            {"item_id": s.item_id, "response": s.response} for s in self_reports
        ],
        "round_event_counts": counts,
    }


async def get_or_create_overreach(
    db: AsyncSession,
    session_id: uuid.UUID,
    *,
    enabled: bool,
    daily_usd_cap: float,
    model: str,
    client: Any | None = None,
) -> InferenceRow:
    """Idempotent: returns the existing row if present, otherwise calls
    the LLM and persists a new row.

    Raises OverreachDisabled / OverreachCostCapHit / OverreachConfigMissing
    when the call cannot proceed and no row exists.
    """
    existing = await existing_overreach_inference(db, session_id)
    if existing is not None:
        return existing

    if not enabled:
        raise OverreachDisabled()

    if await cost_cap.would_exceed_cap(db, daily_usd_cap, EST_CALL_COST_USD):
        raise OverreachCostCapHit()

    summary = await _build_session_summary(db, session_id)
    try:
        result = overreach_engine.score_overreach(summary, client=client, model=model)
    except overreach_engine.OverreachConfigError as e:
        raise OverreachConfigMissing(str(e)) from e

    row = InferenceRow(
        session_id=session_id,
        construct=result.inference.construct,
        tier=result.inference.tier,
        value=result.inference.value,
        confidence=result.inference.confidence,
        evidence=result.inference.evidence,
    )
    db.add(row)
    await db.commit()
    await db.refresh(row)
    await cost_cap.record_spend(db, result.cost_usd)
    return row
