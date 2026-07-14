"""调度 Service：执行历史。"""

from __future__ import annotations

import threading
from datetime import datetime

from src.model.scheduler.schedule_job_model import ScheduleJobModel
from src.model.scheduler.schedule_run_model import ScheduleRunModel
from src.scheduler.runner import execute_job


class ScheduleRunService:
    def __init__(self) -> None:
        self._run_model = ScheduleRunModel()
        self._job_model = ScheduleJobModel()

    def list_runs(
        self,
        *,
        job_key: str | None = None,
        page: int = 1,
        count: int = 20,
    ) -> dict:
        job_id = None
        if job_key:
            job = self._job_model.get_by_job_key(job_key)
            if job is None:
                return {"items": [], "total": 0}
            job_id = job.id
        offset = (page - 1) * count
        rows, total = self._run_model.list_runs(job_id=job_id, offset=offset, limit=count)
        job_key_map = self._job_key_map()
        gap_ids = [r.id for r in rows if r.job_id is None]
        gap_meta = self._run_model.first_step_meta_by_run_ids(gap_ids)
        return {
            "items": [
                self._run_to_dict(
                    r,
                    job_key_map.get(r.job_id),
                    gap_meta=gap_meta.get(r.id),
                )
                for r in rows
            ],
            "total": total,
        }

    def get_run(self, run_id: int) -> dict | None:
        run = self._run_model.get_run(run_id)
        if run is None:
            return None
        job_key = None
        if run.job_id is not None:
            job = self._job_model.get_by_id(run.job_id)
            job_key = job.job_key if job else None
        steps = self._run_model.list_steps_for_run(run_id)
        gap_meta = None
        if run.job_id is None and steps:
            gap_meta = (steps[0].command_key, len(steps))
        data = self._run_to_dict(run, job_key, gap_meta=gap_meta)
        data["steps"] = [self._step_to_dict(s) for s in steps]
        return data

    def trigger_job_async(self, job_key: str, *, triggered_by: str = "admin") -> int:
        job = self._job_model.get_by_job_key(job_key)
        if job is None:
            raise ValueError(f"job not found: {job_key}")

        run_ids: list[int] = []
        event = threading.Event()

        def _worker() -> None:
            execute_job(
                job.id,
                triggered_by=triggered_by,
                run_id_out=run_ids,
                on_run_created=lambda _rid: event.set(),
            )

        thread = threading.Thread(target=_worker, name=f"schedule_run_{job_key}", daemon=True)
        thread.start()
        event.wait(timeout=5)
        if run_ids:
            return run_ids[0]
        raise RuntimeError("触发执行失败")

    def cancel_run(self, run_id: int) -> dict:
        """停止执行中的 run：优先向本进程线程发信号；无活线程则直接写库。"""
        from src.scheduler import cancel as cancel_ctl

        run = self._run_model.get_run(run_id)
        if run is None:
            raise ValueError(f"run not found: {run_id}")
        if run.status != "running":
            raise ValueError(f"run 不在运行中: status={run.status}")

        live = cancel_ctl.request_cancel(run_id)
        if live:
            # 保持 running，等 Strategy 在日循环边界收尾，避免重叠检查被提前放行
            return {
                "ok": True,
                "run_id": run_id,
                "live_signal": True,
                "message": "已发送停止信号，当前交易日结束后停止",
            }

        ok = self._run_model.cancel_run(
            run_id,
            finished_at=datetime.now(),
            error_message="用户停止",
        )
        if not ok:
            raise ValueError(f"run 不在运行中: {run_id}")
        return {
            "ok": True,
            "run_id": run_id,
            "live_signal": False,
            "message": "已标记停止（无对应执行线程，残留记录已清理）",
        }

    def abandon_orphan_runs(self) -> int:
        return self._run_model.abandon_orphan_runs()

    def recent_runs(self, limit: int = 10) -> list[dict]:
        rows = self._run_model.recent_runs(limit=limit)
        job_key_map = self._job_key_map()
        gap_ids = [r.id for r in rows if r.job_id is None]
        gap_meta = self._run_model.first_step_meta_by_run_ids(gap_ids)
        return [
            self._run_to_dict(r, job_key_map.get(r.job_id), gap_meta=gap_meta.get(r.id))
            for r in rows
        ]

    def last_run_at(self) -> str | None:
        dt = self._run_model.last_run_at()
        return dt.strftime("%Y%m%dT%H%M%S") if dt else None

    def _job_key_map(self) -> dict[int, str]:
        return {job.id: job.job_key for job in self._job_model.list_jobs()}

    def _run_to_dict(
        self,
        run,
        job_key: str | None,
        *,
        gap_meta: tuple[str, int] | None = None,
    ) -> dict:
        display_key = job_key
        if display_key is None and gap_meta is not None:
            first_key, step_count = gap_meta
            if run.triggered_by == "gap_fill_row":
                display_key = f"补位行×{step_count}" if step_count > 1 else f"补位:{first_key}"
            elif run.triggered_by == "gap_fill":
                display_key = f"补位:{first_key}"
            else:
                display_key = first_key
        return {
            "run_id": run.id,
            "job_id": run.job_id,
            "job_key": display_key,
            "triggered_by": run.triggered_by,
            "status": run.status,
            "started_at": run.started_at.isoformat() if run.started_at else None,
            "finished_at": run.finished_at.isoformat() if run.finished_at else None,
            "error_message": run.error_message,
        }

    def _step_to_dict(self, step) -> dict:
        return {
            "step_id": step.id,
            "command_key": step.command_key,
            "sort_order": step.sort_order,
            "status": step.status,
            "saved_count": step.saved_count,
            "message": step.message,
            "started_at": step.started_at.isoformat() if step.started_at else None,
            "finished_at": step.finished_at.isoformat() if step.finished_at else None,
        }
