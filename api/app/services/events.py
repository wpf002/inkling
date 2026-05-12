"""Round-agnostic ingestion + retrieval of round events."""
import uuid
from collections.abc import Sequence

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.round_event import RoundEvent
from app.schemas.round import RoundEventBatch
from app.services.content import valid_round_ids


class UnknownRound(Exception):
    def __init__(self, round_id: str):
        super().__init__(f"unknown round: {round_id}")
        self.round_id = round_id


def ensure_known_round(round_id: str) -> None:
    if round_id not in valid_round_ids():
        raise UnknownRound(round_id)


async def ingest_round_events(
    db: AsyncSession, session_id: uuid.UUID, batch: RoundEventBatch
) -> int:
    ensure_known_round(batch.round)
    rows = [
        RoundEvent(
            session_id=session_id,
            round=batch.round,
            event_type=ev.event_type,
            payload=ev.payload,
            t_ms=ev.t_ms,
        )
        for ev in batch.events
    ]
    db.add_all(rows)
    await db.commit()
    return len(rows)


async def fetch_round_events(
    db: AsyncSession, session_id: uuid.UUID, round_id: str
) -> Sequence[RoundEvent]:
    result = await db.execute(
        select(RoundEvent)
        .where(RoundEvent.session_id == session_id, RoundEvent.round == round_id)
        .order_by(RoundEvent.t_ms, RoundEvent.id)
    )
    return result.scalars().all()
