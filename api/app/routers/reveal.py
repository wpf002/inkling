"""Reveal-level endpoints (everything except the Overreach endpoint,
which lives in `routers/overreach.py` so its surface stays narrow).

Endpoints:
  POST /sessions/{token}/reveal-event       - Level-entry instrumentation
  POST /sessions/{token}/stated-vs-revealed - Level 1 compute + persist
  POST /sessions/{token}/broker-pricing     - Level 5 compute + persist
  GET  /sessions/{token}/targeting          - Level 6 ad/scam/recruiter selection
  POST /sessions/{token}/share-card         - Level 8 share-card metadata
"""
import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.deps import require_session_header
from app.schemas.reveal import (
    BrokerPricingResponse,
    RevealEventIn,
    RevealEventResponse,
    ShareCardCreate,
    ShareCardResponse,
    StatedVsRevealedResponse,
    TargetingResponse,
)
from app.schemas.round import InferenceOut
from app.services import reveal as reveal_service
from app.services import reveal_events as reveal_events_service
from app.services import sessions as session_service
from app.services import share_cards as share_cards_service

router = APIRouter(prefix="/sessions", tags=["reveal"])


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


def _to_out(row) -> InferenceOut:
    return InferenceOut(
        construct=row.construct,
        tier=row.tier,
        value=row.value,
        confidence=row.confidence,
        evidence=row.evidence,
    )


@router.post(
    "/{token}/reveal-event",
    response_model=RevealEventResponse,
    status_code=status.HTTP_201_CREATED,
)
async def post_reveal_event(
    token: str,
    payload: RevealEventIn,
    db: AsyncSession = Depends(get_db),
    header_token: str = Depends(require_session_header),
):
    _ensure_token_match(token, header_token)
    session_id = await _resolve_session(db, token)
    await reveal_events_service.record_reveal_event(
        db,
        session_id,
        event_type=payload.event_type,
        payload=payload.payload,
        t_ms=payload.t_ms,
    )
    return RevealEventResponse()


@router.post(
    "/{token}/stated-vs-revealed",
    response_model=StatedVsRevealedResponse,
    status_code=status.HTTP_200_OK,
)
async def post_stated_vs_revealed(
    token: str,
    db: AsyncSession = Depends(get_db),
    header_token: str = Depends(require_session_header),
):
    _ensure_token_match(token, header_token)
    session_id = await _resolve_session(db, token)
    row = await reveal_service.get_or_create_stated_vs_revealed(db, session_id)
    return StatedVsRevealedResponse(inference=_to_out(row) if row is not None else None)


@router.post(
    "/{token}/broker-pricing",
    response_model=BrokerPricingResponse,
    status_code=status.HTTP_200_OK,
)
async def post_broker_pricing(
    token: str,
    db: AsyncSession = Depends(get_db),
    header_token: str = Depends(require_session_header),
):
    _ensure_token_match(token, header_token)
    session_id = await _resolve_session(db, token)
    row = await reveal_service.get_or_create_broker_pricing(db, session_id)
    return BrokerPricingResponse(inference=_to_out(row))


@router.get(
    "/{token}/targeting",
    response_model=TargetingResponse,
    status_code=status.HTTP_200_OK,
)
async def get_targeting(
    token: str,
    db: AsyncSession = Depends(get_db),
    header_token: str = Depends(require_session_header),
):
    _ensure_token_match(token, header_token)
    session_id = await _resolve_session(db, token)
    payload = await reveal_service.compute_targeting(db, session_id)
    return TargetingResponse(**payload)


@router.post(
    "/{token}/share-card",
    response_model=ShareCardResponse,
    status_code=status.HTTP_201_CREATED,
)
async def post_share_card(
    token: str,
    payload: ShareCardCreate,
    db: AsyncSession = Depends(get_db),
    header_token: str = Depends(require_session_header),
):
    _ensure_token_match(token, header_token)
    session_id = await _resolve_session(db, token)
    row = await share_cards_service.create_share_card(
        db,
        session_id,
        image_dimensions=payload.image_dimensions,
        headline=payload.headline,
        inference_id=payload.inference_id,
    )
    return ShareCardResponse(
        id=row.id,
        image_dimensions=row.image_dimensions,
        headline=row.headline,
        inference_id=row.inference_id,
    )
