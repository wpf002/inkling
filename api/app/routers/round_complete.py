import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.deps import require_session_header
from app.schemas.round import (
    InferenceOut,
    RoundCompleteRequest,
    RoundCompleteResponse,
)
from app.services import events as events_service
from app.services import scoring as scoring_service
from app.services import sessions as session_service

router = APIRouter(prefix="/sessions", tags=["round-complete"])


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


def _serialize(rows) -> list[InferenceOut]:
    return [
        InferenceOut(
            construct=r.construct,
            tier=r.tier,
            value=r.value,
            confidence=r.confidence,
            evidence=r.evidence,
        )
        for r in rows
    ]


@router.post(
    "/{token}/round-complete",
    response_model=RoundCompleteResponse,
    status_code=status.HTTP_200_OK,
)
async def post_round_complete(
    token: str,
    payload: RoundCompleteRequest,
    db: AsyncSession = Depends(get_db),
    header_token: str = Depends(require_session_header),
):
    _ensure_token_match(token, header_token)
    session_id = await _resolve_session(db, token)
    try:
        rows = await scoring_service.score_and_persist_round(db, session_id, payload.round)
    except events_service.UnknownRound as e:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, f"unknown round: {e.round_id}") from e
    return RoundCompleteResponse(inferences=_serialize(rows))


@router.get(
    "/{token}/inferences",
    response_model=RoundCompleteResponse,
)
async def get_inferences(
    token: str,
    round: str = Query(..., min_length=1, max_length=32),
    db: AsyncSession = Depends(get_db),
    header_token: str = Depends(require_session_header),
):
    _ensure_token_match(token, header_token)
    session_id = await _resolve_session(db, token)
    try:
        events_service.ensure_known_round(round)
    except events_service.UnknownRound as e:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, f"unknown round: {e.round_id}") from e
    rows = await scoring_service.existing_inferences_for_round(db, session_id, round)
    return RoundCompleteResponse(inferences=_serialize(rows))
