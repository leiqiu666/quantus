from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Body, Depends, HTTPException
from fastapi.responses import StreamingResponse

from src.api.deps import verify_api_token
from src.api.schemas.etl_sse import EtlSseRunRequest, EtlSseSequenceRequest
from src.common.sse import sse_event_stream, SSE_HEADERS
from src.scheduler import cancel as cancel_ctl
from src.service.etl.etl_sse_registry import get_sse_task_runner, validate_sse_task_key
from src.service.etl.completeness_dashboard_service import CompletenessDashboardService
from src.service.scheduler.gap_fill_run_service import (
    GapFillRunTracker,
    GapFillStepSpec,
    run_tracked_gap_fill,
)

router = APIRouter(
    prefix="/etl",
    tags=["etl-sse"],
    dependencies=[Depends(verify_api_token)],
)

_SSE_DESC = (
    "通用 ETL 补位 SSE：task_key 映射 Strategy.check_complete / pull / report_history_init。"
    " report history init 类仅使用 start_date 作为报告期锚点。"
    " task_key=backtest_run 时使用扩展字段 backtest_mode / factor_name / combo_id 等。"
    " task_key=gtja191_compute 时可传 workers。"
    " task_key=factor_compute 时必传 factor_name，可选 force。"
    " 执行写入 schedule_run（triggered_by=gap_fill），可在执行历史查看/停止。"
)

_TASK_LABELS = {
    "backtest_run": "回测",
    "gtja191_compute": "国泰191计算",
    "factor_compute": "因子计算",
}


def _task_label(task_key: str) -> str:
    return _TASK_LABELS.get(task_key, task_key)


def _invoke_runner(body: EtlSseRunRequest, end: str, q) -> None:
    runner = get_sse_task_runner(body.task_key)
    if body.task_key == "backtest_run":
        runner(
            body.start_date,
            end,
            q,
            backtest_mode=body.backtest_mode or "single",
            factor_name=body.factor_name,
            combo_id=body.combo_id,
            groups=body.groups or 10,
            rebalance=body.rebalance or "monthly",
            commission_rate=body.commission_rate,
            stamp_duty_rate=body.stamp_duty_rate,
            slippage_rate=body.slippage_rate,
        )
    elif body.task_key == "gtja191_compute":
        runner(body.start_date, end, q, workers=body.workers)
    elif body.task_key == "factor_compute":
        runner(
            body.start_date,
            end,
            q,
            factor_name=body.factor_name,
            force=bool(body.force),
        )
    else:
        runner(body.start_date, end, q)


@router.post(
    "/sse/run",
    summary="ETL 补位任务（SSE）",
    description=_SSE_DESC,
)
async def run_etl_sse(
    body: Annotated[EtlSseRunRequest, Body()],
) -> StreamingResponse:
    try:
        validate_sse_task_key(body.task_key)
    except KeyError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e

    end = body.end_date or datetime.now().strftime("%Y%m%d")
    label = _task_label(body.task_key)

    if body.task_key == "factor_compute" and not body.factor_name:
        raise HTTPException(status_code=400, detail="factor_compute 需要 factor_name")

    def _worker(q):
        run_tracked_gap_fill(
            progress_queue=q,
            task_key=body.task_key,
            label=label,
            start_date=body.start_date,
            end_date=end,
            triggered_by="gap_fill",
            execute=lambda bridge: _invoke_runner(body, end, bridge),
        )

    return StreamingResponse(
        sse_event_stream(_worker, thread_name=f"etl_sse_{body.task_key}"),
        media_type="text/event-stream",
        headers=SSE_HEADERS,
    )


def _verify_step_completeness(
    *,
    group_id: str,
    date_key: str,
    column_key: str,
    step_label: str,
    threshold: float,
) -> None:
    resp = CompletenessDashboardService().get_dashboard(
        group_id,
        start=date_key,
        end=date_key,
        page=1,
        count=1,
    )
    row = next((item for item in resp["items"] if item.get("date_key") == date_key), None)
    if row is None:
        raise RuntimeError(f"{step_label}：无法验证完整度，未找到日期 {date_key}")
    columns = row.get("columns") or {}
    metric = columns.get(column_key)
    if metric is None:
        raise RuntimeError(f"{step_label}：无法验证完整度，未找到列 {column_key}")
    period_stock_count = int(metric.get("period_stock_count") or 0)
    if period_stock_count <= 0:
        return
    ratio = metric.get("ratio")
    if ratio is None:
        ratio = float(metric.get("count") or 0) / period_stock_count
    if float(ratio) < threshold:
        raise RuntimeError(
            f"{step_label}：数据完整度 {float(ratio) * 100:.1f}%"
            f"（{metric.get('count')}/{period_stock_count}），"
            f"低于 {threshold * 100:.0f}%"
        )


@router.post(
    "/sse/run-sequence",
    summary="行级补位任务（SSE，多列串行）",
    description=(
        "一整行多列串行补位：一条 schedule_run + 每列一个 step（triggered_by=gap_fill_row）。"
        " 关页面不中断；可在执行历史停止。"
    ),
)
async def run_etl_sse_sequence(
    body: Annotated[EtlSseSequenceRequest, Body()],
) -> StreamingResponse:
    for step in body.steps:
        try:
            validate_sse_task_key(step.task_key)
        except KeyError as e:
            raise HTTPException(status_code=400, detail=str(e)) from e

    specs = [
        GapFillStepSpec(
            command_key=s.task_key,
            label=s.label,
            start_date=s.start_date,
            end_date=s.end_date,
            column_key=s.column_key,
            threshold=s.threshold,
        )
        for s in body.steps
    ]

    def _worker(q):
        tracker = GapFillRunTracker()
        tracker.begin_run(
            triggered_by="gap_fill_row",
            steps=specs,
            display_name=body.name,
        )
        tracker.emit_run_id(q)
        total = len(specs)
        q.put({"status": "running", "total": total, "run_id": tracker.run_id})
        failed = 0
        first_error: str | None = None

        for i, step in enumerate(body.steps):
            if tracker.is_cancelled():
                tracker.close_cancelled(step_index=i)
                q.put({
                    "done": True,
                    "run_id": tracker.run_id,
                    "status": "cancelled",
                    "message": "任务已停止",
                })
                return

            tracker.mark_step_running(i)
            bridge = tracker.wrap_progress(
                q,
                cmd_index=i + 1,
                cmd_total=total,
                cmd_label=step.label,
            )
            bridge.put({"status": "running", "total": 1})
            end = step.end_date or step.start_date
            runner = get_sse_task_runner(step.task_key)
            try:
                # 吞掉 runner 内部 done，由序列 worker 统一收尾
                class _NoDoneBridge:
                    def __init__(self, inner):
                        self._inner = inner

                    def put(self, item):
                        if isinstance(item, dict) and (
                            item.get("done") is True or "error" in item
                        ):
                            return
                        self._inner.put(item)

                    def is_cancelled(self):
                        return self._inner.is_cancelled()

                wrapped = _NoDoneBridge(bridge)
                runner(step.start_date, end, wrapped)

                if tracker.is_cancelled():
                    tracker.close_cancelled(step_index=i)
                    q.put({
                        "done": True,
                        "run_id": tracker.run_id,
                        "status": "cancelled",
                        "message": "任务已停止",
                    })
                    return

                if (
                    body.dashboard_group_id
                    and body.dashboard_date_key
                    and step.column_key
                ):
                    _verify_step_completeness(
                        group_id=body.dashboard_group_id,
                        date_key=body.dashboard_date_key,
                        column_key=step.column_key,
                        step_label=step.label,
                        threshold=step.threshold if step.threshold is not None else 0.95,
                    )

                tracker.finish_step(i, status="success", message=f"{step.label} 完成")
                q.put({
                    "index": i + 1,
                    "total": total,
                    "period": step.label,
                    "saved": 0,
                })
            except cancel_ctl.CommandCancelled:
                tracker.close_cancelled(step_index=i)
                q.put({
                    "done": True,
                    "run_id": tracker.run_id,
                    "status": "cancelled",
                    "message": "任务已停止",
                })
                return
            except Exception as exc:
                failed += 1
                err = str(exc)
                if first_error is None:
                    first_error = err
                tracker.finish_step(i, status="failed", message=err)
                q.put({"log": f"错误 · {step.label}：{err}"})

        if failed == 0:
            tracker.close_success()
            q.put({
                "done": True,
                "run_id": tracker.run_id,
                "status": "success",
                "message": f"行级补位完成，共 {total} 列",
            })
        elif failed == total:
            tracker.close_failed(error_message=first_error or "全部失败")
            q.put({"error": first_error or "全部失败", "run_id": tracker.run_id})
        else:
            tracker.close_partial(error_message=first_error)
            q.put({
                "done": True,
                "run_id": tracker.run_id,
                "status": "partial",
                "message": f"部分完成：{total - failed}/{total} 成功",
            })

    return StreamingResponse(
        sse_event_stream(_worker, thread_name="etl_sse_row_sequence"),
        media_type="text/event-stream",
        headers=SSE_HEADERS,
    )
