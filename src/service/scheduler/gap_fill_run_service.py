"""补位任务写入 schedule_run / schedule_run_step，并接入取消信号。"""

from __future__ import annotations

import queue
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Callable

from src.model.scheduler.schedule_run_model import ScheduleRunModel
from src.scheduler import cancel as cancel_ctl
from src.scheduler.progress_bridge import CommandProgressBridge


@dataclass
class GapFillStepSpec:
    command_key: str
    label: str
    start_date: str
    end_date: str | None = None
    column_key: str | None = None
    threshold: float | None = None


class GapFillRunTracker:
    """为 ETL 补位 SSE worker 创建执行历史并桥接进度/取消。"""

    def __init__(self) -> None:
        self._run_model = ScheduleRunModel()
        self.run_id: int | None = None
        self.step_ids: list[int] = []
        self.triggered_by: str = "gap_fill"
        self._closed = False

    def begin_run(
        self,
        *,
        triggered_by: str,
        steps: list[GapFillStepSpec],
        display_name: str | None = None,
    ) -> int:
        now = datetime.now()
        run = self._run_model.create_run(
            job_id=None,
            triggered_by=triggered_by,
            status="running",
            started_at=now,
        )
        self.run_id = run.id
        self.triggered_by = triggered_by
        cancel_ctl.register_run(run.id)

        self.step_ids = []
        for i, step in enumerate(steps):
            range_label = step.start_date
            if step.end_date and step.end_date != step.start_date:
                range_label = f"{step.start_date}~{step.end_date}"
            msg = step.label
            if display_name and i == 0:
                msg = f"{display_name} · {step.label}"
            msg = f"{msg} ({range_label})"
            row = self._run_model.create_step(
                run_id=run.id,
                command_key=step.command_key[:64],
                sort_order=i,
                status="pending",
                message=msg,
            )
            self.step_ids.append(row.id)
        return run.id

    def emit_run_id(self, progress_queue: queue.Queue | None) -> None:
        if progress_queue is not None and self.run_id is not None:
            progress_queue.put({"run_id": self.run_id})

    def wrap_progress(
        self,
        outer: queue.Queue | None,
        *,
        cmd_index: int,
        cmd_total: int,
        cmd_label: str,
    ) -> CommandProgressBridge:
        assert self.run_id is not None
        return CommandProgressBridge(
            outer,
            cmd_index=cmd_index,
            cmd_total=cmd_total,
            cmd_label=cmd_label,
            run_id=self.run_id,
        )

    def mark_step_running(self, step_index: int) -> None:
        self._run_model.update_step(
            self.step_ids[step_index],
            status="running",
            started_at=datetime.now(),
        )

    def finish_step(
        self,
        step_index: int,
        *,
        status: str,
        saved_count: int | None = None,
        message: str | None = None,
    ) -> None:
        kwargs: dict[str, Any] = {
            "status": status,
            "finished_at": datetime.now(),
        }
        if saved_count is not None:
            kwargs["saved_count"] = saved_count
        if message is not None:
            kwargs["message"] = message
        self._run_model.update_step(self.step_ids[step_index], **kwargs)

    def is_cancelled(self) -> bool:
        if self.run_id is None:
            return False
        return cancel_ctl.is_cancel_requested(self.run_id)

    def close_success(self) -> None:
        if self._closed or self.run_id is None:
            return
        self._closed = True
        self._run_model.finish_run(
            self.run_id,
            status="success",
            finished_at=datetime.now(),
        )
        cancel_ctl.unregister_run(self.run_id)

    def close_partial(self, *, error_message: str | None = None) -> None:
        if self._closed or self.run_id is None:
            return
        self._closed = True
        self._run_model.finish_run(
            self.run_id,
            status="partial",
            finished_at=datetime.now(),
            error_message=error_message,
        )
        cancel_ctl.unregister_run(self.run_id)

    def close_failed(self, *, error_message: str) -> None:
        if self._closed or self.run_id is None:
            return
        self._closed = True
        self._run_model.finish_run(
            self.run_id,
            status="failed",
            finished_at=datetime.now(),
            error_message=error_message,
        )
        cancel_ctl.unregister_run(self.run_id)

    def close_cancelled(self, *, step_index: int | None = None) -> None:
        if self._closed or self.run_id is None:
            return
        self._closed = True
        now = datetime.now()
        steps = self._run_model.list_steps_for_run(self.run_id)
        for row in steps:
            if row.status in ("pending", "running"):
                self._run_model.update_step(
                    row.id,
                    status="cancelled",
                    message="用户停止",
                    finished_at=now,
                )
        self._run_model.cancel_run(
            self.run_id,
            finished_at=now,
            error_message="用户停止",
        )
        cancel_ctl.unregister_run(self.run_id)


class CancelAwareQueue:
    """透传进度帧，并提供 is_cancelled() 供 Strategy 循环检查。"""

    def __init__(self, outer: queue.Queue, run_id: int) -> None:
        self._outer = outer
        self._run_id = run_id

    def put(self, item: dict[str, Any]) -> None:
        if not isinstance(item, dict):
            return
        # done/error 由 tracker 统一发，避免双结束帧
        if item.get("done") is True or "error" in item:
            return
        self._outer.put(item)

    def is_cancelled(self) -> bool:
        return cancel_ctl.is_cancel_requested(self._run_id)


def run_tracked_gap_fill(
    *,
    progress_queue: queue.Queue,
    task_key: str,
    label: str,
    start_date: str,
    end_date: str | None = None,
    triggered_by: str = "gap_fill",
    execute: Callable[[Any], None],
) -> None:
    """列级补位：建 run/step，execute(cancel_aware_q)，收尾并保证 done/error 帧。"""
    tracker = GapFillRunTracker()
    tracker.begin_run(
        triggered_by=triggered_by,
        steps=[
            GapFillStepSpec(
                command_key=task_key,
                label=label,
                start_date=start_date,
                end_date=end_date,
            )
        ],
    )
    assert tracker.run_id is not None
    tracker.emit_run_id(progress_queue)
    tracker.mark_step_running(0)
    # 列级走原 ETL 进度帧（index/total/period），同时可取消
    bridge = CancelAwareQueue(progress_queue, tracker.run_id)
    try:
        execute(bridge)
        if tracker.is_cancelled():
            tracker.close_cancelled(step_index=0)
            progress_queue.put({
                "done": True,
                "run_id": tracker.run_id,
                "status": "cancelled",
                "message": "任务已停止",
            })
            return
        tracker.finish_step(0, status="success")
        tracker.close_success()
        progress_queue.put({
            "done": True,
            "run_id": tracker.run_id,
            "status": "success",
            "message": "任务完成",
        })
    except cancel_ctl.CommandCancelled:
        tracker.close_cancelled(step_index=0)
        progress_queue.put({
            "done": True,
            "run_id": tracker.run_id,
            "status": "cancelled",
            "message": "任务已停止",
        })
    except Exception as exc:
        tracker.finish_step(0, status="failed", message=str(exc))
        tracker.close_failed(error_message=str(exc))
        progress_queue.put({"error": str(exc), "run_id": tracker.run_id})
