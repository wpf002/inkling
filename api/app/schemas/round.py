import warnings
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

MAX_EVENTS_PER_BATCH = 200


class RoundEventIn(BaseModel):
    model_config = ConfigDict(extra="ignore")

    event_type: str = Field(min_length=1, max_length=64)
    payload: dict[str, Any] = Field(default_factory=dict)
    t_ms: int = Field(ge=0)


class RoundEventBatch(BaseModel):
    round: str = Field(min_length=1, max_length=32)
    events: list[RoundEventIn] = Field(min_length=1, max_length=MAX_EVENTS_PER_BATCH)


class RoundEventBatchResponse(BaseModel):
    accepted: int


class RoundCompleteRequest(BaseModel):
    round: str = Field(min_length=1, max_length=32)


# `construct` is the canonical field name in the public schema. Pydantic
# warns it shadows BaseModel.construct (deprecated alias for model_construct);
# silence locally rather than rename.
with warnings.catch_warnings():
    warnings.filterwarnings(
        "ignore",
        message=r'Field name "construct"',
        category=UserWarning,
    )

    class InferenceOut(BaseModel):
        model_config = ConfigDict(protected_namespaces=())

        construct: str
        tier: str
        value: dict[str, Any]
        confidence: float
        evidence: dict[str, Any]


class RoundCompleteResponse(BaseModel):
    inferences: list[InferenceOut]
