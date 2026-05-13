"""Reveal instrumentation events.

The reveal page logs a `reveal_level_entered` event on every level
view. We persist these into `round_events` with `round = "reveal"` so
the column can hold both gameplay and reveal events without schema
churn. The unknown-round validation in `events.py` is bypassed here
because "reveal" is not a gameplay round.
"""
from __future__ import annotations

import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.round_event import RoundEvent

REVEAL_ROUND_KEY = "reveal"


async def record_reveal_event(
    db: AsyncSession,
    session_id: uuid.UUID,
    *,
    event_type: str,
    payload: dict,
    t_ms: int,
) -> None:
    row = RoundEvent(
        session_id=session_id,
        round=REVEAL_ROUND_KEY,
        event_type=event_type,
        payload=payload,
        t_ms=t_ms,
    )
    db.add(row)
    await db.commit()
