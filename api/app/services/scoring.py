"""Round-agnostic bridge from stored events → engine → persisted inferences."""
import uuid

from inkling_engine import score_round
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.inference import Inference as InferenceRow
from app.models.round_event import RoundEvent
from app.services.events import ensure_known_round, fetch_round_events


def _round_inference_constructs(round_id: str) -> set[str]:
    """Pre-load the manifest's listed constructs for a round.

    Used to detect "already scored" without coupling to a specific round.
    """
    from app.services.content import load_round_manifest

    for r in load_round_manifest()["rounds"]:
        if r["id"] == round_id:
            return set(r.get("constructs", []))
    return set()


def _row_from_engine_event(ev: RoundEvent) -> dict:
    return {
        "event_type": ev.event_type,
        "payload": ev.payload or {},
        "t_ms": ev.t_ms,
    }


async def existing_inferences_for_round(
    db: AsyncSession, session_id: uuid.UUID, round_id: str
) -> list[InferenceRow]:
    constructs = _round_inference_constructs(round_id)
    if not constructs:
        return []
    result = await db.execute(
        select(InferenceRow)
        .where(
            InferenceRow.session_id == session_id,
            InferenceRow.construct.in_(constructs),
        )
        .order_by(InferenceRow.id)
    )
    return list(result.scalars().all())


async def score_and_persist_round(
    db: AsyncSession, session_id: uuid.UUID, round_id: str
) -> list[InferenceRow]:
    """Idempotent: returns existing inferences if already scored."""
    ensure_known_round(round_id)

    existing = await existing_inferences_for_round(db, session_id, round_id)
    if existing:
        return existing

    events = await fetch_round_events(db, session_id, round_id)
    payloads = [_row_from_engine_event(ev) for ev in events]
    inferences = score_round(round_id, payloads)

    rows = [
        InferenceRow(
            session_id=session_id,
            construct=inf.construct,
            tier=inf.tier,
            value=inf.value,
            confidence=inf.confidence,
            evidence=inf.evidence,
        )
        for inf in inferences
    ]
    db.add_all(rows)
    await db.commit()
    for row in rows:
        await db.refresh(row)
    return rows
