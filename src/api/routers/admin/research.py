"""投研分析 Router。"""

from typing import Annotated, Optional

from fastapi import APIRouter, Depends, HTTPException, Query

from src.api.deps import verify_api_token
from src.api.schemas.research import (
    FactorCsResponse,
    QuoteResponse,
    StockKlineResponse,
)
from src.service.research.research_query_service import ResearchQueryService

router = APIRouter(
    prefix="/research",
    tags=["投研分析"],
    dependencies=[Depends(verify_api_token)],
)


@router.get(
    "/factor-cs",
    summary="因子截面",
    response_model=FactorCsResponse,
)
def get_factor_cs(
    trade_date: Annotated[str, Query(pattern=r"^\d{8}$")],
    factor_name: Optional[str] = Query(default=None),
    combo_id: Optional[int] = Query(default=None, ge=1),
) -> FactorCsResponse:
    if not factor_name and combo_id is None:
        raise HTTPException(status_code=400, detail="需要 factor_name 或 combo_id")
    try:
        data = ResearchQueryService().factor_cs(
            trade_date=trade_date,
            factor_name=factor_name,
            combo_id=combo_id,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    return FactorCsResponse.model_validate(data)


@router.get(
    "/stock-kline",
    summary="个股日K",
    response_model=StockKlineResponse,
)
def get_stock_kline(
    ts_code: Annotated[str, Query(min_length=1)],
    start: Annotated[str, Query(pattern=r"^\d{8}$")],
    end: Annotated[str, Query(pattern=r"^\d{8}$")],
    factor_name: Optional[str] = Query(default=None),
) -> StockKlineResponse:
    try:
        data = ResearchQueryService().stock_kline(
            ts_code=ts_code,
            start=start,
            end=end,
            factor_name=factor_name,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    return StockKlineResponse.model_validate(data)


@router.get(
    "/quote",
    summary="行情快照",
    response_model=QuoteResponse,
)
def get_quote(
    ts_code: Annotated[str, Query(min_length=1)],
) -> QuoteResponse:
    try:
        data = ResearchQueryService().quote(ts_code)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    return QuoteResponse.model_validate(data)
