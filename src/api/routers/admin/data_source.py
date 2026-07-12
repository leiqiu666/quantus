from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Body, Depends, HTTPException, Query

from src.api.deps import verify_api_token
from src.api.schemas.data_source_dashboard import (
    DashboardRequest,
    DashboardResponse,
)
from src.api.schemas.data_source_overview import OverviewResponse
from src.service.etl.completeness_dashboard_config import DASHBOARD_GROUPS
from src.service.etl.completeness_dashboard_service import CompletenessDashboardService
from src.service.etl.completeness_overview_service import CompletenessOverviewService

router = APIRouter(
    prefix="/data-source",
    tags=["data-source"],
    dependencies=[Depends(verify_api_token)],
)


@router.get(
    "/groups",
    summary="列出看板分组",
    description="返回 Admin 量化数据源看板可用 group_id 与标题。",
)
def list_dashboard_groups() -> list[dict[str, str]]:
    return [
        {"group_id": g.group_id, "title": g.title, "date_key_type": g.date_key_type}
        for g in DASHBOARD_GROUPS.values()
    ]


@router.get(
    "/overview",
    summary="量化数据源总览",
    description=(
        "跨 6 个看板分组的最近窗口完整性摘要、待处理缺口、"
        "关键路径滞后与调度任务摘要。"
    ),
    response_model=OverviewResponse,
)
def get_overview(
    window: Annotated[int, Query(ge=1, le=30, description="最近窗口条数（日/期/月）")] = 5,
) -> OverviewResponse:
    data = CompletenessOverviewService().get_overview(window=window)
    return OverviewResponse.model_validate(data)


@router.post(
    "/dashboard",
    summary="量化数据源看板",
    description=(
        "按 group_id 返回宽表行：每行一个 date_key，每列一个数据源的数量与完整性。"
        "财务三表+指标、K线等专用分组走聚合 Service；其余走 completeness_snapshot 透视。"
    ),
    response_model=DashboardResponse,
)
def get_dashboard(
    body: Annotated[
        DashboardRequest,
        Body(default_factory=DashboardRequest),
    ],
) -> DashboardResponse:
    if body.group_id not in DASHBOARD_GROUPS:
        raise HTTPException(status_code=400, detail=f"unknown group_id: {body.group_id}")
    try:
        result = CompletenessDashboardService().get_dashboard(
            body.group_id,
            start=body.start,
            end=body.end,
            page=body.page,
            count=body.count,
        )
    except KeyError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    return DashboardResponse.model_validate(result)
