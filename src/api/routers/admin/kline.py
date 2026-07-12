from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Body, Depends

from src.api.deps import verify_api_token
from src.api.schemas.kline_daily import (
    KlineDailyDateListRequest,
    KlineDailyDateListResponse,
)
from src.common.function import trade_date_page_bounds
from src.common.setting import settings
from src.service.kline.kline_daily_service import KlineDailyService
from src.service.stock.stock_trade_cal_service import TradeCalService

router = APIRouter(
    prefix="/kline",
    tags=["kline"],
    dependencies=[Depends(verify_api_token)],
)


def _default_start_date() -> str:
    return settings.etl_start_date("kline_daily")


@router.post(
    "/daily/trade-date-list",
    summary="获取日 K 交易日列表",
    description=(
        "按 SSE 开市日返回各 trade_date 的 kline_daily、复权因子条数；period_stock_count 实时按 stock_list 计算。"
        "先在日期区间内用开市日序列分页（见 src.common.function.trade_date_page_bounds），"
        "起点、终点省略时分别为 KLINE_DAILY_START_DATE（或 ETL_DEFAULT_START_DATE）与当天；page 从 1 起，第 1 页为最新开市日。"
        "本页对应的日历下界与上界传给服务层聚合查询；仅返回库中在该窗口内出现数据的交易日（无数据的交易日不占行）。"
        "total 为区间内 SSE 开市日总数，供前端分页。"
    ),
    response_model=KlineDailyDateListResponse,
)
def get_trade_date_list(
    body: Annotated[
        KlineDailyDateListRequest,
        Body(
            default_factory=KlineDailyDateListRequest,
            description=(
                "可省略或传空对象。"
                "start_date / end_date：YYYYMMDD；"
                "page / count：分页（默认 page=1、count=50）。"
            ),
        ),
    ],
) -> KlineDailyDateListResponse:
    """同步路由：FastAPI 会在线程池中执行。"""
    start_bound = body.start_date or _default_start_date()
    end_bound = body.end_date or datetime.now().strftime("%Y%m%d")

    open_dates = TradeCalService().get_open_trade_dates(
        start_date=start_bound,
        end_date=end_bound,
    )
    total = len(open_dates)

    bounds = trade_date_page_bounds(
        start_bound, end_bound, body.page, body.count
    )
    if bounds is None:
        return KlineDailyDateListResponse(items=[], total=total)
    window_lo, window_hi = bounds

    items = KlineDailyService().get_trade_date_list(
        start_date=window_lo,
        end_date=window_hi,
    )
    return KlineDailyDateListResponse(items=items, total=total)
