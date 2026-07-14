"""调度系统 Admin Router。"""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Body, Depends, HTTPException, Path
from fastapi.responses import StreamingResponse

from src.api.deps import verify_api_token
from src.api.schemas.scheduler import (
    ScheduleCommandItem,
    ScheduleJobCreateRequest,
    ScheduleJobItem,
    ScheduleJobUpdateRequest,
    ScheduleOverviewResponse,
    ScheduleRunItem,
    ScheduleRunListRequest,
    ScheduleRunListResponse,
)
from src.common.sse import SSE_HEADERS, sse_event_stream
from src.model.scheduler.schedule_job_model import ScheduleJobModel
from src.scheduler.runner import execute_job
from src.service.scheduler.schedule_job_service import ScheduleJobService
from src.service.scheduler.schedule_overview_service import ScheduleOverviewService
from src.service.scheduler.schedule_run_service import ScheduleRunService

router = APIRouter(
    prefix="/scheduler",
    tags=["调度系统"],
    dependencies=[Depends(verify_api_token)],
)


@router.get(
    "/commands",
    summary="ETL 命令清单",
    description="返回 25 条可调度 ETL 菜单命令及任务引用关系。",
    response_model=list[ScheduleCommandItem],
)
def list_commands() -> list[ScheduleCommandItem]:
    items = ScheduleOverviewService().list_commands()
    return [ScheduleCommandItem.model_validate(item) for item in items]


@router.get(
    "/overview",
    summary="调度看板",
    description="命令覆盖统计与最近执行记录。",
    response_model=ScheduleOverviewResponse,
)
def get_overview() -> ScheduleOverviewResponse:
    data = ScheduleOverviewService().get_overview()
    return ScheduleOverviewResponse.model_validate(data)


@router.get(
    "/jobs",
    summary="调度任务列表",
    response_model=list[ScheduleJobItem],
)
def list_jobs() -> list[ScheduleJobItem]:
    items = ScheduleJobService().list_jobs()
    return [ScheduleJobItem.model_validate(item) for item in items]


@router.post(
    "/jobs",
    summary="创建调度任务",
    response_model=ScheduleJobItem,
)
def create_job(
    body: Annotated[ScheduleJobCreateRequest, Body()],
) -> ScheduleJobItem:
    try:
        item = ScheduleJobService().create_job(body.model_dump())
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return ScheduleJobItem.model_validate(item)


@router.get(
    "/jobs/{job_key}",
    summary="调度任务详情",
    response_model=ScheduleJobItem,
)
def get_job(
    job_key: Annotated[str, Path(description="任务唯一键")],
) -> ScheduleJobItem:
    item = ScheduleJobService().get_job(job_key)
    if item is None:
        raise HTTPException(status_code=404, detail=f"job not found: {job_key}")
    return ScheduleJobItem.model_validate(item)


@router.patch(
    "/jobs/{job_key}",
    summary="更新调度任务",
    response_model=ScheduleJobItem,
)
def update_job(
    job_key: Annotated[str, Path(description="任务唯一键")],
    body: Annotated[ScheduleJobUpdateRequest, Body()],
) -> ScheduleJobItem:
    payload = body.model_dump(exclude_unset=True)
    try:
        item = ScheduleJobService().update_job(job_key, payload)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    if item is None:
        raise HTTPException(status_code=404, detail=f"job not found: {job_key}")
    return ScheduleJobItem.model_validate(item)


@router.delete(
    "/jobs/{job_key}",
    summary="删除调度任务",
)
def delete_job(
    job_key: Annotated[str, Path(description="任务唯一键")],
) -> dict[str, bool]:
    ok = ScheduleJobService().delete_job(job_key)
    if not ok:
        raise HTTPException(status_code=404, detail=f"job not found: {job_key}")
    return {"ok": True}


@router.post(
    "/jobs/{job_key}/run",
    summary="手动触发调度任务（SSE）",
    description="串行执行绑定的 ETL 命令，推送进度帧：running / index+total / done。",
)
async def trigger_job(
    job_key: Annotated[str, Path(description="任务唯一键")],
) -> StreamingResponse:
    job = ScheduleJobModel().get_by_job_key(job_key)
    if job is None:
        raise HTTPException(status_code=404, detail=f"job not found: {job_key}")

    job_id = job.id

    def _worker(q) -> None:
        execute_job(job_id, triggered_by="admin", progress_queue=q)

    return StreamingResponse(
        sse_event_stream(_worker, thread_name=f"schedule_run_{job_key}"),
        media_type="text/event-stream",
        headers=SSE_HEADERS,
    )


@router.post(
    "/runs",
    summary="执行历史分页",
    response_model=ScheduleRunListResponse,
)
def list_runs(
    body: Annotated[ScheduleRunListRequest, Body()],
) -> ScheduleRunListResponse:
    data = ScheduleRunService().list_runs(
        job_key=body.job_key,
        page=body.page,
        count=body.count,
    )
    return ScheduleRunListResponse(
        items=[ScheduleRunItem.model_validate(item) for item in data["items"]],
        total=data["total"],
    )


@router.get(
    "/runs/{run_id}",
    summary="执行详情",
    response_model=ScheduleRunItem,
)
def get_run(
    run_id: Annotated[int, Path(description="执行记录 ID")],
) -> ScheduleRunItem:
    item = ScheduleRunService().get_run(run_id)
    if item is None:
        raise HTTPException(status_code=404, detail=f"run not found: {run_id}")
    return ScheduleRunItem.model_validate(item)


@router.post(
    "/runs/{run_id}/cancel",
    summary="停止执行中的任务",
    description="标记 run 为 cancelled，并向本进程内执行线程发送停止信号（当前交易日结束后不再继续）。",
)
def cancel_run(
    run_id: Annotated[int, Path(description="执行记录 ID")],
) -> dict:
    try:
        return ScheduleRunService().cancel_run(run_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
