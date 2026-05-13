"""API-side wrappers for the rule-based reveal modules.

Three idempotent compute-and-persist helpers (one per Inference row
type used in the reveal):
  - stated_vs_revealed: Level 1 comparison
  - broker_pricing:    Level 5 pricing breakdown
  - targeting:         Level 6 ads/scams/recruiter selection (NOT
                        persisted as an Inference — returned ad-hoc per
                        session because it depends on which content
                        files are loaded; persist if we later want to
                        snapshot the version the player saw)

All three pull the persisted inferences + self-report rows for the
session and shell out to `inkling_engine.reveal.*` for the actual logic.
"""
from __future__ import annotations

import json
import uuid
from pathlib import Path
from typing import Any

from inkling_engine.reveal import pricing, stated_vs_revealed, targeting
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.inference import Inference as InferenceRow
from app.models.self_report import SelfReport

REPO_ROOT = Path(__file__).resolve().parents[3]
ADS_PATH = REPO_ROOT / "content" / "ads" / "templates.json"
SCAMS_PATH = REPO_ROOT / "content" / "scams" / "templates.json"
RECRUITER_PATH = REPO_ROOT / "content" / "recruiter" / "templates.json"


async def _all_inferences(
    db: AsyncSession, session_id: uuid.UUID
) -> list[InferenceRow]:
    result = await db.execute(
        select(InferenceRow)
        .where(InferenceRow.session_id == session_id)
        .order_by(InferenceRow.id)
    )
    return list(result.scalars().all())


async def _self_reports(
    db: AsyncSession, session_id: uuid.UUID
) -> list[SelfReport]:
    result = await db.execute(
        select(SelfReport).where(SelfReport.session_id == session_id)
    )
    return list(result.scalars().all())


def _to_dicts(rows: list[InferenceRow]) -> list[dict[str, Any]]:
    return [
        {
            "construct": r.construct,
            "tier": r.tier,
            "value": r.value,
            "confidence": r.confidence,
        }
        for r in rows
    ]


async def get_or_create_stated_vs_revealed(
    db: AsyncSession, session_id: uuid.UUID
) -> InferenceRow | None:
    """Returns None if the player has fewer than 6 round inferences (the
    Layer-1 punch isn't meaningful otherwise)."""
    existing = await db.execute(
        select(InferenceRow).where(
            InferenceRow.session_id == session_id,
            InferenceRow.construct == "stated_vs_revealed",
        )
    )
    found = existing.scalar_one_or_none()
    if found is not None:
        return found

    rows = await _all_inferences(db, session_id)
    round_inferences = [r for r in rows if r.tier in ("high", "medium")]
    if len(round_inferences) < 6:
        return None

    self_reports = await _self_reports(db, session_id)
    pairs = stated_vs_revealed.compute_pairs(
        _to_dicts(round_inferences),
        [{"item_id": s.item_id, "response": s.response} for s in self_reports],
    )
    if not pairs:
        return None

    value = stated_vs_revealed.build_inference_value(pairs)
    row = InferenceRow(
        session_id=session_id,
        construct="stated_vs_revealed",
        tier="high",
        value=value,
        confidence=1.0,
        evidence={"pair_count": len(pairs)},
    )
    db.add(row)
    await db.commit()
    await db.refresh(row)
    return row


async def get_or_create_broker_pricing(
    db: AsyncSession, session_id: uuid.UUID
) -> InferenceRow:
    existing = await db.execute(
        select(InferenceRow).where(
            InferenceRow.session_id == session_id,
            InferenceRow.construct == "broker_pricing",
        )
    )
    found = existing.scalar_one_or_none()
    if found is not None:
        return found

    rows = await _all_inferences(db, session_id)
    round_inferences = [r for r in rows if r.tier in ("high", "medium")]
    overreach_row = next((r for r in rows if r.construct == "overreach"), None)
    overreach_value = overreach_row.value if overreach_row is not None else None
    value = pricing.price_profile(_to_dicts(round_inferences), overreach_value)

    row = InferenceRow(
        session_id=session_id,
        construct="broker_pricing",
        tier="overreach",
        value=value,
        confidence=0.5,
        evidence={"includes_overreach": overreach_row is not None},
    )
    db.add(row)
    await db.commit()
    await db.refresh(row)
    return row


async def compute_targeting(
    db: AsyncSession, session_id: uuid.UUID
) -> dict[str, Any]:
    rows = await _all_inferences(db, session_id)
    round_inferences = [r for r in rows if r.tier in ("high", "medium")]
    ads = json.loads(ADS_PATH.read_text())["templates"]
    scams = json.loads(SCAMS_PATH.read_text())["templates"]
    recruiter = json.loads(RECRUITER_PATH.read_text())["templates"]
    return targeting.select(_to_dicts(round_inferences), ads, scams, recruiter)
