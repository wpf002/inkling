import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models._types import BigIntPk, UUIDType


class ShareCard(Base):
    __tablename__ = "share_cards"

    id: Mapped[int] = mapped_column(BigIntPk, primary_key=True, autoincrement=True)
    session_id: Mapped[uuid.UUID] = mapped_column(
        UUIDType, ForeignKey("sessions.id", ondelete="CASCADE"), nullable=False, index=True
    )
    image_dimensions: Mapped[str] = mapped_column(String(16), nullable=False)
    headline: Mapped[str] = mapped_column(String(256), nullable=False)
    inference_id: Mapped[int | None] = mapped_column(
        BigIntPk, ForeignKey("inferences.id", ondelete="SET NULL"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    session: Mapped["Session"] = relationship(back_populates="share_cards")  # noqa: F821
