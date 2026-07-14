"""调度任务串行执行：写 run / step 日志并调 command registry。"""

from __future__ import annotations

import logging
import queue
from collections.abc import Callable
from datetime import datetime

from src.model.scheduler.schedule_job_model import ScheduleJobModel
from src.model.scheduler.schedule_run_model import ScheduleRunModel
from src.scheduler import cancel as cancel_ctl
from src.scheduler.command_registry import get_command_spec, run_command
from src.scheduler.progress_bridge import CommandProgressBridge
from src.service.stock.stock_trade_cal_service import TradeCalService

logger = logging.getLogger(__name__)


def _notify_run_created(
    run_id: int,
    *,
    run_id_out: list[int] | None,
    on_run_created: Callable[[int], None] | None,
) -> None:
    if run_id_out is not None:
        run_id_out.append(run_id)
    if on_run_created is not None:
        on_run_created(run_id)


def _now() -> datetime:
    return datetime.now()


def is_sse_trading_day(date_key: str | None = None) -> bool:
    key = date_key or _now().strftime("%Y%m%d")
    dates = TradeCalService().get_open_trade_dates(start_date=key, end_date=key)
    return key in dates


def _sse_put(progress_queue: queue.Queue | None, item: dict) -> None:
    if progress_queue is not None:
        progress_queue.put(item)


def execute_job(
    job_id: int,
    *,
    triggered_by: str = "cron",
    skip_trading_day_check: bool = False,
    skip_overlap_check: bool = False,
    run_id_out: list[int] | None = None,
    on_run_created: Callable[[int], None] | None = None,
    progress_queue: queue.Queue | None = None,
) -> int | None:
    job_model = ScheduleJobModel()
    run_model = ScheduleRunModel()
    job = job_model.get_by_id(job_id)
    if job is None:
        raise ValueError(f"job not found: {job_id}")

    if not skip_overlap_check and run_model.has_running_for_job(job_id):
        logger.info("skip job %s: already running", job.job_key)
        _sse_put(progress_queue, {"error": "该任务已有运行中的实例，请稍后再试"})
        return None

    if (
        not skip_trading_day_check
        and job.run_on_trading_day
        and not is_sse_trading_day()
    ):
        run = run_model.create_run(
            job_id=job_id,
            triggered_by=triggered_by,
            status="skipped",
            started_at=_now(),
        )
        run_model.finish_run(
            run.id,
            status="skipped",
            finished_at=_now(),
            error_message="非 SSE 开市日，跳过执行",
        )
        _notify_run_created(
            run.id,
            run_id_out=run_id_out,
            on_run_created=on_run_created,
        )
        _sse_put(progress_queue, {
            "done": True,
            "message": "非 SSE 开市日，已跳过",
            "run_id": run.id,
        })
        return run.id

    commands = job_model.list_commands_for_job(job_id)
    if not commands:
        run = run_model.create_run(
            job_id=job_id,
            triggered_by=triggered_by,
            status="failed",
            started_at=_now(),
        )
        run_model.finish_run(
            run.id,
            status="failed",
            finished_at=_now(),
            error_message="任务未绑定任何命令",
        )
        _notify_run_created(
            run.id,
            run_id_out=run_id_out,
            on_run_created=on_run_created,
        )
        _sse_put(progress_queue, {"error": "任务未绑定任何命令"})
        return run.id

    run = run_model.create_run(
        job_id=job_id,
        triggered_by=triggered_by,
        status="running",
        started_at=_now(),
    )
    cancel_ctl.register_run(run.id)
    _notify_run_created(
        run.id,
        run_id_out=run_id_out,
        on_run_created=on_run_created,
    )

    failed = 0
    cancelled = False
    first_error: str | None = None
    total = len(commands)
    _sse_put(progress_queue, {"status": "running", "total": total, "run_id": run.id})

    try:
        for idx, cmd in enumerate(commands, start=1):
            if cancel_ctl.is_cancel_requested(run.id):
                cancelled = True
                break

            step = run_model.create_step(
                run_id=run.id,
                command_key=cmd.command_key,
                sort_order=cmd.sort_order,
                status="running",
                started_at=_now(),
            )
            spec = get_command_spec(cmd.command_key)
            bridge = CommandProgressBridge(
                progress_queue,
                cmd_index=idx,
                cmd_total=total,
                cmd_label=spec.label,
                run_id=run.id,
            )
            # 进入命令即推 0%，Admin 立刻显示「第 N/M 步 label 0%」
            bridge.put({"status": "running", "total": 1})
            try:
                saved = run_command(cmd.command_key, progress_queue=bridge)
                if cancel_ctl.is_cancel_requested(run.id):
                    run_model.cancel_run(
                        run.id,
                        finished_at=_now(),
                        error_message="用户停止",
                    )
                    run_model.update_step(
                        step.id,
                        status="cancelled",
                        saved_count=saved,
                        message="用户停止",
                        finished_at=_now(),
                    )
                    _sse_put(progress_queue, {
                        "index": idx,
                        "total": total,
                        "period": spec.label,
                        "saved": saved if saved is not None else 0,
                        "log": f"第 {idx}/{total} 步 {spec.label} 已停止",
                    })
                    cancelled = True
                    break
                message = f"完成，写入 {saved} 条" if saved is not None else "完成"
                run_model.update_step(
                    step.id,
                    status="success",
                    saved_count=saved,
                    message=message,
                    finished_at=_now(),
                )
                _sse_put(progress_queue, {
                    "index": idx,
                    "total": total,
                    "period": spec.label,
                    "saved": saved if saved is not None else 0,
                })
            except cancel_ctl.CommandCancelled:
                cancelled = True
                run_model.cancel_run(
                    run.id,
                    finished_at=_now(),
                    error_message="用户停止",
                )
                run_model.update_step(
                    step.id,
                    status="cancelled",
                    message="用户停止",
                    finished_at=_now(),
                )
                _sse_put(progress_queue, {
                    "log": f"第 {idx}/{total} 步 {spec.label} 已停止",
                })
                break
            except Exception as exc:
                failed += 1
                err = str(exc)
                if first_error is None:
                    first_error = err
                logger.exception("command %s failed in job %s", cmd.command_key, job.job_key)
                run_model.update_step(
                    step.id,
                    status="failed",
                    message=err,
                    finished_at=_now(),
                )
                _sse_put(progress_queue, {
                    "index": idx,
                    "total": total,
                    "period": spec.label,
                    "saved": 0,
                })

        if cancelled:
            # cancel_run 可能已由 API 写过；此处兜底保证终态
            current = run_model.get_run(run.id)
            if current is not None and current.status == "running":
                run_model.cancel_run(
                    run.id,
                    finished_at=_now(),
                    error_message="用户停止",
                )
            final_status = "cancelled"
            done_msg = "任务已停止"
        elif failed == 0:
            final_status = "success"
            done_msg = f"任务完成，共 {total} 条命令"
        elif failed == len(commands):
            final_status = "failed"
            done_msg = first_error or "全部命令失败"
        else:
            final_status = "partial"
            done_msg = f"部分完成：{total - failed}/{total} 成功"

        if not cancelled:
            run_model.finish_run(
                run.id,
                status=final_status,
                finished_at=_now(),
                error_message=first_error,
            )
        _sse_put(progress_queue, {
            "done": True,
            "message": done_msg,
            "run_id": run.id,
            "status": final_status,
        })
        return run.id
    finally:
        cancel_ctl.unregister_run(run.id)
