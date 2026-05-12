import warnings
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

Tier = Literal["high", "medium", "overreach"]


class RoundEventDTO(BaseModel):
    model_config = ConfigDict(extra="ignore")

    event_type: str
    payload: dict[str, Any] = Field(default_factory=dict)
    t_ms: int


# `construct` is the canonical field name in the public schema; pydantic
# warns that it shadows BaseModel.construct (deprecated alias for
# model_construct). Silence locally so importing the engine is quiet.
with warnings.catch_warnings():
    warnings.filterwarnings(
        "ignore",
        message=r'Field name "construct"',
        category=UserWarning,
    )

    class Inference(BaseModel):
        model_config = ConfigDict(protected_namespaces=())

        construct: str
        tier: Tier
        value: dict[str, Any]
        confidence: float = Field(ge=0.0, le=1.0)
        evidence: dict[str, Any] = Field(default_factory=dict)
