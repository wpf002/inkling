from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db, get_session_factory
from app.deps import require_session_header
from app.schemas.self_report import SelfReportSubmission, SelfReportSubmissionResponse
from app.schemas.session import (
    ConsentPayload,
    SessionCreate,
    SessionCreateResponse,
    SessionState,
)
from app.services import sessions as session_service

router = APIRouter(prefix="/sessions", tags=["sessions"])


def _ensure_token_match(token_in_path: str, token_in_header: str) -> None:
    if token_in_path != token_in_header:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="X-Inkling-Session does not match path token",
        )


@router.post("", response_model=SessionCreateResponse, status_code=status.HTTP_201_CREATED)
async def create_session(payload: SessionCreate, db: AsyncSession = Depends(get_db)):
    try:
        session = await session_service.create_session(db, payload)
    except session_service.SessionConflict as e:
        raise HTTPException(status.HTTP_409_CONFLICT, detail=str(e)) from e
    return SessionCreateResponse(
        session_id=session.id,
        anonymous_token=session.anonymous_token,
        created_at=session.created_at,
    )


@router.get("/{token}", response_model=SessionState)
async def get_session(
    token: str,
    db: AsyncSession = Depends(get_db),
    header_token: str = Depends(require_session_header),
):
    _ensure_token_match(token, header_token)
    try:
        session = await session_service.get_session_by_token(db, token)
    except session_service.SessionNotFound as e:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "session not found") from e
    return SessionState(
        session_id=session.id,
        anonymous_token=session.anonymous_token,
        consent=ConsentPayload(**session.consent),
        age_attested=session.age_attested,
        has_self_report=await session_service.has_self_report(db, session.id),
        completed_at=session.completed_at,
        created_at=session.created_at,
    )


async def _hard_delete_in_background(session_id) -> None:
    async with get_session_factory()() as db:
        await session_service.hard_delete_session(db, session_id)


@router.delete("/{token}", status_code=status.HTTP_202_ACCEPTED)
async def delete_session(
    token: str,
    background: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
    header_token: str = Depends(require_session_header),
):
    _ensure_token_match(token, header_token)
    try:
        session = await session_service.get_session_by_token(db, token)
    except session_service.SessionNotFound as e:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "session not found") from e
    await session_service.soft_delete_session(db, session)
    background.add_task(_hard_delete_in_background, session.id)
    return {"status": "deleting", "session_id": str(session.id)}


@router.post(
    "/{token}/self-report",
    response_model=SelfReportSubmissionResponse,
    status_code=status.HTTP_201_CREATED,
)
async def submit_self_report(
    token: str,
    payload: SelfReportSubmission,
    db: AsyncSession = Depends(get_db),
    header_token: str = Depends(require_session_header),
):
    _ensure_token_match(token, header_token)
    try:
        session = await session_service.get_session_by_token(db, token)
    except session_service.SessionNotFound as e:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "session not found") from e
    try:
        saved = await session_service.submit_self_report(db, session, payload)
    except session_service.AgeAttestationRequired as e:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "age attestation required") from e
    except session_service.UnknownSelfReportItem as e:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_ENTITY,
            f"unknown item_ids: {e.item_ids}",
        ) from e
    except session_service.SelfReportAlreadySubmitted as e:
        raise HTTPException(status.HTTP_409_CONFLICT, "self-report already submitted") from e
    return SelfReportSubmissionResponse(saved=saved)
