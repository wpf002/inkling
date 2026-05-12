from fastapi import APIRouter, HTTPException, Query, status

from app.schemas.self_report import SelfReportItemDef, SelfReportItemsResponse
from app.services.content import (
    load_round_content,
    load_round_gambles,
    load_self_report_items,
)
from app.services.events import UnknownRound, ensure_known_round

router = APIRouter(prefix="/content", tags=["content"])


@router.get("/self-report-items", response_model=SelfReportItemsResponse)
async def self_report_items():
    items = [SelfReportItemDef.model_validate(i) for i in load_self_report_items()]
    return SelfReportItemsResponse(items=items)


@router.get("/round-gambles")
async def round_gambles(round: str = Query(..., min_length=1, max_length=32)):
    try:
        ensure_known_round(round)
    except UnknownRound as e:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, f"unknown round: {e.round_id}") from e
    try:
        return load_round_gambles(round)
    except FileNotFoundError as e:
        raise HTTPException(
            status.HTTP_404_NOT_FOUND, f"round has no gambles content: {round}"
        ) from e


@router.get("/round-content")
async def round_content(round: str = Query(..., min_length=1, max_length=32)):
    """Round-agnostic content fetch: returns the JSON declared by the
    manifest's `content_file` field for this round."""
    try:
        ensure_known_round(round)
    except UnknownRound as e:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, f"unknown round: {e.round_id}") from e
    try:
        return load_round_content(round)
    except FileNotFoundError as e:
        raise HTTPException(
            status.HTTP_404_NOT_FOUND, f"round has no declared content_file: {round}"
        ) from e
