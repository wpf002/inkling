from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class ConsentPayload(BaseModel):
    """Itemized consent. Each key maps to a category in docs/consent.md."""

    gameplay: bool
    interaction_patterns: bool
    self_report: bool
    retain_profile_7d: bool
    research_aggregate: bool = False


class SessionCreate(BaseModel):
    consent: ConsentPayload
    age_attested: bool
    anonymous_token: str = Field(min_length=8, max_length=64)


class SessionCreateResponse(BaseModel):
    session_id: UUID
    anonymous_token: str
    created_at: datetime


class SessionState(BaseModel):
    session_id: UUID
    anonymous_token: str
    consent: ConsentPayload
    age_attested: bool
    has_self_report: bool
    completed_at: datetime | None
    created_at: datetime
    completed_rounds: list[str] = Field(default_factory=list)
    next_round: str | None = None
