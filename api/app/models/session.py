import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import Boolean, DateTime, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models._types import JSONType, UUIDType


class Session(Base):
    __tablename__ = "sessions"

    id: Mapped[uuid.UUID] = mapped_column(UUIDType, primary_key=True, default=uuid.uuid4)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    anonymous_token: Mapped[str] = mapped_column(
        String(64), nullable=False, unique=True, index=True
    )
    consent: Mapped[dict[str, Any]] = mapped_column(JSONType, nullable=False)
    age_attested: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    self_reports: Mapped[list["SelfReport"]] = relationship(  # noqa: F821
        back_populates="session", cascade="all, delete-orphan", passive_deletes=True
    )
    round_events: Mapped[list["RoundEvent"]] = relationship(  # noqa: F821
        back_populates="session", cascade="all, delete-orphan", passive_deletes=True
    )
    inferences: Mapped[list["Inference"]] = relationship(  # noqa: F821
        back_populates="session", cascade="all, delete-orphan", passive_deletes=True
    )
    share_cards: Mapped[list["ShareCard"]] = relationship(  # noqa: F821
        back_populates="session", cascade="all, delete-orphan", passive_deletes=True
    )
    research_optins: Mapped[list["ResearchOptIn"]] = relationship(  # noqa: F821
        back_populates="session", cascade="all, delete-orphan", passive_deletes=True
    )
