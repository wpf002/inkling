"""Pydantic request/response shapes for the Phase 3 reveal endpoints."""
from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field

from app.schemas.round import InferenceOut


class RevealEventIn(BaseModel):
    event_type: str = Field(min_length=1, max_length=64)
    payload: dict[str, Any] = Field(default_factory=dict)
    t_ms: int = Field(ge=0)


class RevealEventResponse(BaseModel):
    accepted: bool = True


class OverreachResponse(BaseModel):
    inference: InferenceOut
    cached: bool


class StatedVsRevealedResponse(BaseModel):
    inference: InferenceOut | None


class BrokerPricingResponse(BaseModel):
    inference: InferenceOut


class TargetingResponse(BaseModel):
    ads: list[dict[str, Any]]
    scams: list[dict[str, Any]]
    recruiter: list[dict[str, Any]]
    top_constructs: list[str]


class ShareCardCreate(BaseModel):
    image_dimensions: str = Field(min_length=3, max_length=16)
    headline: str = Field(min_length=1, max_length=256)
    inference_id: int | None = None


class ShareCardResponse(BaseModel):
    id: int
    image_dimensions: str
    headline: str
    inference_id: int | None
