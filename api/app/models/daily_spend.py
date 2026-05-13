"""Daily Anthropic-spend tracker for the Overreach cost cap.

One row per UTC date. The Overreach service increments `total_usd` and
`call_count` after each successful (non-idempotent) LLM call. The cost
cap is checked against today's row before each new call.
"""
from datetime import date, datetime

from sqlalchemy import Date, DateTime, Float, Integer, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class DailySpend(Base):
    __tablename__ = "daily_spend"

    date: Mapped[date] = mapped_column(Date, primary_key=True, nullable=False)
    total_usd: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    call_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
