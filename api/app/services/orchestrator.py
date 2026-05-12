"""Round orchestrator helpers.

Given a session, derive `completed_rounds` and `next_round` from the
inferences table + the manifest. We derive (not store) so that the
truth-source is the data that already exists.

Round-agnostic: walks the manifest in order, doesn't hardcode round ids.
"""
import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.inference import Inference as InferenceRow
from app.services.content import manifest_rounds_in_order


async def completed_round_ids(
    db: AsyncSession, session_id: uuid.UUID
) -> list[str]:
    """Return the round ids the player has finished, in manifest order."""
    result = await db.execute(
        select(InferenceRow.construct).where(InferenceRow.session_id == session_id)
    )
    constructs_present = {row[0] for row in result.all()}

    done: list[str] = []
    for r in manifest_rounds_in_order():
        round_constructs = set(r.get("constructs", []))
        if round_constructs and round_constructs.issubset(constructs_present):
            done.append(r["id"])
    return done


def next_round_id(completed: list[str]) -> str | None:
    """First manifest round_id not in `completed`, or None if all are done."""
    done = set(completed)
    for r in manifest_rounds_in_order():
        if r["id"] not in done:
            return r["id"]
    return None
