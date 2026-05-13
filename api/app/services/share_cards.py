"""Share-card metadata persistence.

The image bytes are generated client-side via html2canvas and never
leave the browser. The server stores only metadata so that we can:
  - count cards generated per session (analytics, post-launch)
  - cascade-delete with the session
"""
from __future__ import annotations

import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.share_card import ShareCard


async def create_share_card(
    db: AsyncSession,
    session_id: uuid.UUID,
    *,
    image_dimensions: str,
    headline: str,
    inference_id: int | None,
) -> ShareCard:
    row = ShareCard(
        session_id=session_id,
        image_dimensions=image_dimensions,
        headline=headline,
        inference_id=inference_id,
    )
    db.add(row)
    await db.commit()
    await db.refresh(row)
    return row
