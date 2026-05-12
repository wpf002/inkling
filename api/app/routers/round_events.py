import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.deps import require_session_header
from app.schemas.round import RoundEventBatch, RoundEventBatchResponse
from app.services import events as events_service
from app.services import sessions as session_service

router = APIRouter(prefix="/sessions", tags=["round-events"])


def _ensure_token_match(token_in_path: str, token_in_header: str) -> None:
    if token_in_path != token_in_header:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="X-Inkling-Session does not match path token",
        )


async def _resolve_session(db: AsyncSession, token: str) -> uuid.UUID:
    try:
        session = await session_service.get_session_by_token(db, token)
    except session_service.SessionNotFound as e:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "session not found") from e
    if not session.age_attested:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "age attestation required")
    return session.id


@router.post(
    "/{token}/round-events",
    response_model=RoundEventBatchResponse,
    status_code=status.HTTP_201_CREATED,
)
async def post_round_events(
    token: str,
    payload: RoundEventBatch,
    db: AsyncSession = Depends(get_db),
    header_token: str = Depends(require_session_header),
):
    _ensure_token_match(token, header_token)
    session_id = await _resolve_session(db, token)
    try:
        accepted = await events_service.ingest_round_events(db, session_id, payload)
    except events_service.UnknownRound as e:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, f"unknown round: {e.round_id}") from e
    return RoundEventBatchResponse(accepted=accepted)
