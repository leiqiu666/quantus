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
        return {
            "items": [self._run_to_dict(r, job_key_map.get(r.job_id)) for r in rows],
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
        data = self._run_to_dict(run, job_key)
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

    def recent_runs(self, limit: int = 10) -> list[dict]:
        rows = self._run_model.recent_runs(limit=limit)
        job_key_map = self._job_key_map()
        return [self._run_to_dict(r, job_key_map.get(r.job_id)) for r in rows]

    def last_run_at(self) -> str | None:
        dt = self._run_model.last_run_at()
        return dt.strftime("%Y%m%dT%H%M%S") if dt else None

    def _job_key_map(self) -> dict[int, str]:
        return {job.id: job.job_key for job in self._job_model.list_jobs()}

    def _run_to_dict(self, run, job_key: str | None) -> dict:
        return {
            "run_id": run.id,
            "job_id": run.job_id,
            "job_key": job_key,
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
