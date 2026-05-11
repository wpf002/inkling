import uuid
from typing import Any

from sqlalchemy import BigInteger, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models._types import BigIntPk, JSONType, UUIDType


class RoundEvent(Base):
    __tablename__ = "round_events"

    id: Mapped[int] = mapped_column(BigIntPk, primary_key=True, autoincrement=True)
    session_id: Mapped[uuid.UUID] = mapped_column(
        UUIDType, ForeignKey("sessions.id", ondelete="CASCADE"), nullable=False, index=True
    )
    round: Mapped[str] = mapped_column(String(32), nullable=False)
    event_type: Mapped[str] = mapped_column(String(64), nullable=False)
    payload: Mapped[dict[str, Any]] = mapped_column(JSONType, nullable=False)
    t_ms: Mapped[int] = mapped_column(BigInteger, nullable=False)

    session: Mapped["Session"] = relationship(back_populates="round_events")  # noqa: F821
