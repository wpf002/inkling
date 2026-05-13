"""Daily Anthropic-spend tracker.

The single endpoint that consumes paid Anthropic credit (the Overreach
LLM call) checks `would_exceed_cap` before issuing a request and
`record_spend` after a successful one. The check is best-effort: a
single race between concurrent requests can overshoot by one call. For
the soft launch this is acceptable; tighten with row-level locking if
the call rate ever rises above one per second.
"""
from __future__ import annotations

from datetime import UTC, date, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.daily_spend import DailySpend


def _today() -> date:
    return datetime.now(UTC).date()


async def get_today_spend(db: AsyncSession) -> float:
    today = _today()
    result = await db.execute(select(DailySpend).where(DailySpend.date == today))
    row = result.scalar_one_or_none()
    return float(row.total_usd) if row is not None else 0.0


async def would_exceed_cap(db: AsyncSession, cap_usd: float, est_call_usd: float) -> bool:
    if cap_usd <= 0:
        return True
    cur = await get_today_spend(db)
    return (cur + est_call_usd) > cap_usd


async def record_spend(db: AsyncSession, cost_usd: float) -> None:
    today = _today()
    result = await db.execute(select(DailySpend).where(DailySpend.date == today))
    row = result.scalar_one_or_none()
    if row is None:
        row = DailySpend(date=today, total_usd=cost_usd, call_count=1)
        db.add(row)
    else:
        row.total_usd = float(row.total_usd) + cost_usd
        row.call_count = int(row.call_count) + 1
        row.updated_at = datetime.now(UTC)
    await db.commit()
