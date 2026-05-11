import uuid
from datetime import UTC, datetime

from sqlalchemy import delete, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.self_report import SelfReport
from app.models.session import Session
from app.schemas.self_report import SelfReportSubmission
from app.schemas.session import SessionCreate
from app.services.content import valid_item_ids


class SessionConflict(Exception):
    pass


class SessionNotFound(Exception):
    pass


class AgeAttestationRequired(Exception):
    pass


class UnknownSelfReportItem(Exception):
    def __init__(self, item_ids: list[str]):
        super().__init__(f"unknown item_ids: {item_ids}")
        self.item_ids = item_ids


class SelfReportAlreadySubmitted(Exception):
    pass


async def create_session(db: AsyncSession, payload: SessionCreate) -> Session:
    session = Session(
        id=uuid.uuid4(),
        anonymous_token=payload.anonymous_token,
        consent=payload.consent.model_dump(),
        age_attested=payload.age_attested,
    )
    db.add(session)
    try:
        await db.commit()
    except IntegrityError as e:
        await db.rollback()
        raise SessionConflict("anonymous_token already in use") from e
    await db.refresh(session)
    return session


async def get_session_by_token(db: AsyncSession, token: str) -> Session:
    result = await db.execute(
        select(Session).where(Session.anonymous_token == token, Session.deleted_at.is_(None))
    )
    session = result.scalar_one_or_none()
    if session is None:
        raise SessionNotFound(token)
    return session


async def has_self_report(db: AsyncSession, session_id: uuid.UUID) -> bool:
    result = await db.execute(
        select(SelfReport.id).where(SelfReport.session_id == session_id).limit(1)
    )
    return result.first() is not None


async def submit_self_report(
    db: AsyncSession, session: Session, payload: SelfReportSubmission
) -> int:
    if not session.age_attested:
        raise AgeAttestationRequired()

    if await has_self_report(db, session.id):
        raise SelfReportAlreadySubmitted()

    allowed = valid_item_ids()
    bad = [r.item_id for r in payload.responses if r.item_id not in allowed]
    if bad:
        raise UnknownSelfReportItem(bad)

    for r in payload.responses:
        db.add(SelfReport(session_id=session.id, item_id=r.item_id, response=r.response))
    await db.commit()
    return len(payload.responses)


async def soft_delete_session(db: AsyncSession, session: Session) -> None:
    session.deleted_at = datetime.now(UTC)
    await db.commit()


async def hard_delete_session(db: AsyncSession, session_id: uuid.UUID) -> None:
    """Cascades to child tables via FK ondelete='CASCADE'."""
    await db.execute(delete(Session).where(Session.id == session_id))
    await db.commit()
