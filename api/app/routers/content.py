from fastapi import APIRouter

from app.schemas.self_report import SelfReportItemDef, SelfReportItemsResponse
from app.services.content import load_self_report_items

router = APIRouter(prefix="/content", tags=["content"])


@router.get("/self-report-items", response_model=SelfReportItemsResponse)
async def self_report_items():
    items = [SelfReportItemDef.model_validate(i) for i in load_self_report_items()]
    return SelfReportItemsResponse(items=items)
