"""POST /sessions/{token}/overreach — generate the Level-4 overreach.

Idempotent (the engine call is skipped if a row exists). Per-IP rate
limit applies even on cached returns so a runaway client cannot hammer
the endpoint.
"""
import uuid

from fastapi import APIRouter, Depends, Header, HTTPException, Request, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.database import get_db
from app.deps import require_session_header
from app.schemas.reveal import OverreachResponse
from app.schemas.round import InferenceOut
from app.services import overreach as overreach_service
from app.services import sessions as session_service
from app.services.rate_limit import overreach_limiter

router = APIRouter(prefix="/sessions", tags=["overreach"])


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


def _client_ip(request: Request, x_forwarded_for: str | None) -> str:
    if x_forwarded_for:
        return x_forwarded_for.split(",")[0].strip()
    if request.client is not None:
        return request.client.host
    return "unknown"


@router.post(
    "/{token}/overreach",
    response_model=OverreachResponse,
    status_code=status.HTTP_200_OK,
)
async def post_overreach(
    token: str,
    request: Request,
    response: Response,
    db: AsyncSession = Depends(get_db),
    header_token: str = Depends(require_session_header),
    x_forwarded_for: str | None = Header(default=None, alias="X-Forwarded-For"),
):
    _ensure_token_match(token, header_token)
    session_id = await _resolve_session(db, token)
    settings = get_settings()

    ip = _client_ip(request, x_forwarded_for)
    allowed, retry_in = overreach_limiter.check(ip, settings.overreach_rate_limit_per_hour)
    if not allowed:
        # If a cached row exists, idempotency wins over the limit so the
        # player does not lose their reveal.
        cached = await overreach_service.existing_overreach_inference(db, session_id)
        if cached is not None:
            response.headers["X-Overreach-Cached"] = "1"
            return OverreachResponse(
                inference=InferenceOut(
                    construct=cached.construct,
                    tier=cached.tier,
                    value=cached.value,
                    confidence=cached.confidence,
                    evidence=cached.evidence,
                ),
                cached=True,
            )
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=(
                f"Overreach rate limit reached for this IP. Try again in "
                f"about {retry_in // 60 + 1} minutes."
            ),
            headers={"Retry-After": str(retry_in)},
        )

    cached_row = await overreach_service.existing_overreach_inference(db, session_id)
    cached = cached_row is not None
    try:
        row = await overreach_service.get_or_create_overreach(
            db,
            session_id,
            enabled=settings.overreach_enabled,
            daily_usd_cap=settings.overreach_daily_usd_cap,
            model=settings.overreach_model,
        )
    except overreach_service.OverreachDisabled as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Overreach generation is paused (OVERREACH_ENABLED=false).",
        ) from e
    except overreach_service.OverreachCostCapHit as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=(
                "We've hit our daily limit for this part of the reveal. "
                "Everything else still works — come back tomorrow for the rest."
            ),
        ) from e
    except overreach_service.OverreachConfigMissing as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Overreach not configured: {e}",
        ) from e

    return OverreachResponse(
        inference=InferenceOut(
            construct=row.construct,
            tier=row.tier,
            value=row.value,
            confidence=row.confidence,
            evidence=row.evidence,
        ),
        cached=cached,
    )
