from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Body, Depends
from fastapi.responses import StreamingResponse

from src.common.function import report_period_page_bounds
from src.common.sse import sse_streaming_response
from src.api.deps import verify_api_token
from src.api.schemas.financial_report import (
    IncomeHistoryInitRequest,
    ReportPeriodItem,
    ReportPeriodListRequest,
)
from src.service.financial.financial_report_service import ReportService
from src.etl.strategy.financial.financial_report_strategy import ReportStrategy

router = APIRouter(
    prefix="/financial",
    tags=["financial"],
    dependencies=[Depends(verify_api_token)],
)


_SSE_DESC_COMMON = (
    "默认以 Server-Sent Events 流式返回进度：`data:` 后为 JSON。"
    " 首帧多为 {\"status\":\"started\"}；随后 {\"status\":\"running\",\"total\"}；"
    "每期进度：index、total、period、saved；"
    "成功结束帧：done=true 与 periods；失败：error。"
    " 若工具长时间无输出，多为在第一期 ETL 完成前阻塞；请拉长超时或换 curl -N 验证。"
    " SSE/线程模板见 src.common.sse：队列消费使用异步轮询而非默认线程池阻塞读，"
    "避免断连占满线程池导致其它请求饿死。"
    " 任务可能耗时很长，请在 Nginx 等代理上关闭缓冲（如 proxy_buffering off）并放宽 proxy_read_timeout。"
)


@router.post(
    "/report/income-history-init",
    summary="历史利润表全量入库（SSE）",
    description=(
        _SSE_DESC_COMMON
        + " 后台线程执行 strategy.report_income_history_init；"
        "契约模型见 src.api.schemas.financial_report 中 IncomeHistoryInitStream*。"
    ),
)
async def report_income_history_init(
    body: Annotated[
        IncomeHistoryInitRequest,
        Body(
            default_factory=IncomeHistoryInitRequest,
            description="可省略；省略时 start_date 默认为 19900101",
        ),
    ],
) -> StreamingResponse:
    return sse_streaming_response(
        ReportStrategy().report_income_history_init,
        body.start_date,
        thread_name="report_income_history_init",
    )


@router.post(
    "/report/balance-history-init",
    summary="历史资产负债表全量入库（SSE）",
    description=(
        _SSE_DESC_COMMON
        + " 后台线程执行 strategy.report_balance_history_init。"
    ),
)
async def report_balance_history_init(
    body: Annotated[
        IncomeHistoryInitRequest,
        Body(
            default_factory=IncomeHistoryInitRequest,
            description="可省略；省略时 start_date 默认为 19900101",
        ),
    ],
) -> StreamingResponse:
    return sse_streaming_response(
        ReportStrategy().report_balance_history_init,
        body.start_date,
        thread_name="report_balance_history_init",
    )


@router.post(
    "/report/cashflow-history-init",
    summary="历史现金流量表全量入库（SSE）",
    description=(
        _SSE_DESC_COMMON
        + " 后台线程执行 strategy.report_cashflow_history_init。"
    ),
)
async def report_cashflow_history_init(
    body: Annotated[
        IncomeHistoryInitRequest,
        Body(
            default_factory=IncomeHistoryInitRequest,
            description="可省略；省略时 start_date 默认为 19900101",
        ),
    ],
) -> StreamingResponse:
    return sse_streaming_response(
        ReportStrategy().report_cashflow_history_init,
        body.start_date,
        thread_name="report_cashflow_history_init",
    )


@router.post(
    "/report/indicator-history-init",
    summary="历史财务指标全量入库（SSE）",
    description=(
        _SSE_DESC_COMMON
        + " 后台线程执行 strategy.report_indicator_history_init。"
    ),
)
async def report_indicator_history_init(
    body: Annotated[
        IncomeHistoryInitRequest,
        Body(
            default_factory=IncomeHistoryInitRequest,
            description="可省略；省略时 start_date 默认为 19900101",
        ),
    ],
) -> StreamingResponse:
    return sse_streaming_response(
        ReportStrategy().report_indicator_history_init,
        body.start_date,
        thread_name="report_indicator_history_init",
    )

@router.post(
    "/report/period-list",
    summary="获取报告期列表",
    description=(
        "合并利润表、资产负债表、现金流量表、财务指标：按报告期返回各表记录条数。"
        "先在日期区间内用季度末序列分页（见 src.common.function.report_period_page_bounds），"
        "起点、终点省略时分别为 19900101 与当天；page 从 1 起，第 1 页为最新报告期。"
        "本页对应的日历下界与上界传给服务层聚合查询；仅返回库中在该窗口内出现的报告期（无数据的季度不会占行）。"
    ),
    response_model=list[ReportPeriodItem],
)
def get_period_list(
    body: Annotated[
        ReportPeriodListRequest,
        Body(
            default_factory=ReportPeriodListRequest,
            description=(
                "可省略或传空对象。"
                "start_period_date / end_period_date：YYYYMMDD；"
                "page / count：分页（默认 page=1、count=50）。"
            ),
        ),
    ],
) -> list[ReportPeriodItem]:
    """同步路由：FastAPI 会在线程池中执行。"""
    start_bound = body.start_period_date or "19900101"
    end_bound = body.end_period_date or datetime.now().strftime("%Y%m%d")

    bounds = report_period_page_bounds(
        start_bound, end_bound, body.page, body.count
    )
    if bounds is None:
        return []
    window_lo, window_hi = bounds

    return ReportService().get_period_list(
        start_period_date=window_lo,
        end_period_date=window_hi,
    )