from pydantic import BaseModel, ConfigDict, Field


class SelfReportItem(BaseModel):
    item_id: str = Field(min_length=1, max_length=32)
    response: int = Field(ge=1, le=5)


class SelfReportSubmission(BaseModel):
    responses: list[SelfReportItem] = Field(min_length=1)


class SelfReportSubmissionResponse(BaseModel):
    saved: int


class SelfReportItemDef(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    id: str
    construct_name: str = Field(alias="construct", serialization_alias="construct")
    prompt: str
    scale: str


class SelfReportItemsResponse(BaseModel):
    items: list[SelfReportItemDef]
